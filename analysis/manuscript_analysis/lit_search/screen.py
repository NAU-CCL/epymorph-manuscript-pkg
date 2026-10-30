"""
The pre-filter screen: one lexicon, both sources.

A record advances iff all three concept blocks of `lexicon.py` fire in its title, abstract
or keywords. The lexicon is defined once and applied unchanged to PubMed and Lens.org, so
the protocol reported in Appendix S1 §S1.1 and the screen actually executed cannot drift.

Hand-entered dispositions are joined on from `decisions/screen-decisions.csv` and never
written back. That file is the only place a `decision` or `reason` lives; this script
cannot modify it, which is the point. Before the decisions layer existed, the shortlists
carried empty `decision` columns that a re-run would silently have overwritten.

Outputs, all to `results/lit-search/`:
    shortlist-pubmed.csv  shortlist-lens.csv     advanced by the pre-filter
    dropped-pubmed.csv    dropped-lens.csv       set aside, input to the recall audit

Run by `report.py`, which needs its counts.
"""
import csv
import re

from . import paths
from .lexicon import DOM, FILT, KNOWN, METH, SOFT, hits


def norm(text):
    """A title reduced to lowercase words, for matching duplicates across sources."""
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def known_names(text):
    """Display names of the register packages this record mentions, in lexicon order."""
    names = []
    for name, pattern in KNOWN:
        if name not in names and re.search(pattern, text):
            names.append(name)
    return names

FIELDS = ["source", "id", "title", "venue", "year", "doi", "type",
          "soft", "meth", "dom", "filt", "known", "decision", "reason"]


def advances(blob):
    """A record advances iff all three concept blocks fire."""
    return bool(hits(blob, SOFT)) and bool(hits(blob, METH)) and bool(hits(blob, DOM))


def load_decisions():
    """Hand-entered dispositions, keyed by source and id. Absent file is not an error."""
    if not paths.SCREEN_DECISIONS.exists():
        return {}
    return {(row["source"], row["id"]): (row.get("decision", "").strip(),
                                         row.get("reason", "").strip())
            for row in paths.read_rows(paths.SCREEN_DECISIONS)}


def score(source, identifier, title, venue, year, doi, kind, blob, decisions):
    decision, reason = decisions.get((source, identifier), ("", ""))
    return {
        "source": source, "id": identifier, "title": title, "venue": venue,
        "year": year, "doi": doi, "type": kind,
        "soft": len(hits(blob, SOFT)), "meth": len(hits(blob, METH)),
        "dom": len(hits(blob, DOM)), "filt": len(hits(blob, FILT)),
        "known": ";".join(known_names(blob)),
        "decision": decision, "reason": reason,
    }


def read_pubmed(decisions):
    """PubMed: metadata from the CSV export, abstracts from the MEDLINE text export."""
    meta = {}
    with paths.PUBMED_METADATA.open(encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            pmid = (row.get("﻿PMID") or row.get("PMID") or "").strip()
            if pmid:
                meta[pmid] = {"title": row["Title"].strip(),
                              "journal": row["Journal/Book"].strip(),
                              "year": row["Publication Year"].strip(),
                              "doi": row.get("DOI", "").strip()}

    raw = paths.PUBMED_ABSTRACTS.read_text(encoding="utf-8", errors="replace")
    blocks = {}
    for part in re.split(r"\n(?=\d+\.\s+[A-Z])", raw):
        found = re.search(r"^PMID:\s*(\d+)", part, re.M)
        if found:
            blocks[found.group(1)] = part

    advanced, dropped = [], []
    for pmid, block in blocks.items():
        record = meta.get(pmid, {})
        row = score("PubMed", pmid, record.get("title", ""), record.get("journal", ""),
                    record.get("year", ""), record.get("doi", ""), "journal article",
                    block.lower(), decisions)
        (advanced if advances(block.lower()) else dropped).append(row)
    return advanced, dropped, len(blocks), meta


def read_lens(decisions, meta):
    """Lens, de-duplicated against PubMed by PMID, then DOI, then normalized title."""
    with paths.LENS_EXPORT.open(encoding="utf-8-sig", errors="replace") as f:
        records = list(csv.DictReader(f))

    pubmed_titles = {norm(v["title"]) for v in meta.values()}
    pubmed_dois = {v["doi"].lower() for v in meta.values() if v["doi"]}

    duplicates, novel = 0, []
    for record in records:
        pmid = (record.get("PMID") or "").strip()
        doi = (record.get("DOI") or "").strip().lower()
        title = norm(record.get("Title", ""))
        if (pmid and pmid in meta) or (doi and doi in pubmed_dois) or \
                (title and title in pubmed_titles):
            duplicates += 1
        else:
            novel.append(record)

    advanced, dropped = [], []
    for record in novel:
        blob = " ".join([record.get("Title", ""), record.get("Abstract", ""),
                         record.get("Keywords", "")]).lower()
        blob = re.sub("<[^>]+>", " ", blob)
        clean_title = re.sub(r"\s+", " ",
                             re.sub("<[^>]+>", " ", record.get("Title", ""))).strip()
        row = score("Lens", record.get("Lens ID", ""), clean_title,
                    record.get("Source Title", ""), record.get("Publication Year", ""),
                    record.get("DOI", ""), record.get("Publication Type", ""),
                    blob, decisions)
        (advanced if advances(blob) else dropped).append(row)
    return advanced, dropped, len(records), duplicates, len(novel)


def dump(path, rows):
    rows = sorted(rows, key=lambda r: (-r["filt"], -r["soft"], r["title"]))
    paths.write_rows(path, rows, FIELDS)
    return len(rows)


def main():
    decisions = load_decisions()
    pm_advanced, pm_dropped, pm_screened, meta = read_pubmed(decisions)
    ln_advanced, ln_dropped, ln_total, ln_duplicates, ln_novel = read_lens(decisions, meta)

    counts = {
        "pubmed_retrieved": len(meta),
        "pubmed_screened": pm_screened,
        "pubmed_advanced": dump(paths.SHORTLIST_PUBMED, pm_advanced),
        "pubmed_dropped": dump(paths.DROPPED_PUBMED, pm_dropped),
        "lens_retrieved": ln_total,
        "lens_duplicates": ln_duplicates,
        "lens_novel": ln_novel,
        "lens_advanced": dump(paths.SHORTLIST_LENS, ln_advanced),
        "lens_dropped": dump(paths.DROPPED_LENS, ln_dropped),
    }
    counts["total_screened"] = counts["pubmed_screened"] + counts["lens_novel"]
    counts["total_advanced"] = counts["pubmed_advanced"] + counts["lens_advanced"]
    counts["total_dropped"] = counts["pubmed_dropped"] + counts["lens_dropped"]

    print("PubMed")
    print(f"  records retrieved             : {counts['pubmed_retrieved']}")
    print(f"  records with abstracts parsed : {counts['pubmed_screened']}")
    print(f"  advanced by pre-filter        : {counts['pubmed_advanced']}")
    print(f"  dropped                       : {counts['pubmed_dropped']}")
    print("Lens.org")
    print(f"  records retrieved             : {counts['lens_retrieved']}")
    print(f"  duplicates of PubMed          : {counts['lens_duplicates']}")
    print(f"  novel                         : {counts['lens_novel']}")
    print(f"  advanced by pre-filter        : {counts['lens_advanced']}")
    print(f"  dropped                       : {counts['lens_dropped']}")
    print(f"TOTAL unique screened           : {counts['total_screened']}")
    print(f"TOTAL advanced                  : {counts['total_advanced']}")

    # Say out loud how much of the advanced set carries a hand-entered disposition, so
    # that an incomplete decisions file is visible here rather than only to a reviewer.
    advanced = pm_advanced + ln_advanced
    dispositioned = sum(1 for r in advanced if r["decision"])
    counts["advanced_dispositioned"] = dispositioned
    if not decisions:
        print(f"\nno {paths.SCREEN_DECISIONS.name}: decision and reason are empty")
    elif dispositioned == len(advanced):
        print(f"\ndispositions: {dispositioned}/{len(advanced)} - complete")
    else:
        print(f"\ndispositions: {dispositioned}/{len(advanced)} - "
              f"{len(advanced) - dispositioned} still blank in "
              f"{paths.SCREEN_DECISIONS.name}")
    return counts


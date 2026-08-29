"""Orchestrator: discover -> scrape -> web enrich -> LinkedIn enrich -> write to sponsors.xlsx."""
import argparse

import discover
import excel_writer
import linkedin_enrich
import scrape_sponsors
import web_enrich


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-discover", action="store_true")
    parser.add_argument("--skip-scrape", action="store_true")
    parser.add_argument("--skip-web", action="store_true")
    parser.add_argument("--skip-linkedin", action="store_true")
    parser.add_argument("--skip-excel", action="store_true")
    parser.add_argument("--linkedin-dry-run", action="store_true")
    args = parser.parse_args()

    if not args.skip_discover:
        discover.discover()
    if not args.skip_scrape:
        scrape_sponsors.scrape_all()
    if not args.skip_web:
        web_enrich.enrich()
    if not args.skip_linkedin:
        linkedin_enrich.enrich(dry_run=args.linkedin_dry_run)
    if not args.skip_excel:
        excel_writer.sync()


if __name__ == "__main__":
    main()

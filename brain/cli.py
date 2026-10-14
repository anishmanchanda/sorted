"""`brain` command line. Subcommands are added as milestones land."""

import argparse

from sqlalchemy import func, select

from brain import db


def cmd_init(_args) -> None:
    db.init_db()
    print(f"database ready: {db.engine.url}")


def cmd_stats(_args) -> None:
    db.init_db()
    with db.Session() as s:
        for model in db.Base.__subclasses__():
            print(f"{model.__tablename__:16} {s.scalar(select(func.count()).select_from(model))}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="brain")
    sub = p.add_subparsers(required=True)
    sub.add_parser("init", help="create the SQLite schema").set_defaults(fn=cmd_init)
    sub.add_parser("stats", help="row counts per table").set_defaults(fn=cmd_stats)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()

"""Command line for the beer atlas."""

import argparse
from importlib import import_module

COMMANDS = {
    "build": ("build_atlas", "Generate the HTML and web manifest"),
    "preview": ("preview_atlas", "Serve the site locally"),
    "check": (None, "Run browser and release checks"),
    "audit": ("audit_atlas", "Run Lighthouse for mobile and desktop"),
    "audit-report": ("build_site_audit", "Summarize the Lighthouse results"),
    "package": ("package_deliverables", "Make a ZIP from the audited site files"),
    "pdf": ("build_pdf", "Generate the print atlas"),
    "sources": ("read_sources", "Export the verified source catalogue as JSON"),
}


def check(argv):
    parser = argparse.ArgumentParser(prog="atlas check", description=COMMANDS["check"][1])
    parser.parse_args(argv)
    for module in ("check_atlas", "check_navigation", "check_static_site", "check_release"):
        import_module(module).main([])


def main(argv=None):
    commands = "\n".join(f"  {name:14}{description}" for name, (_, description) in COMMANDS.items())
    parser = argparse.ArgumentParser(
        description="Build, check and package the beer atlas.",
        epilog=f"Commands:\n{commands}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", nargs="?", choices=COMMANDS, metavar="COMMAND")
    parser.add_argument("arguments", nargs=argparse.REMAINDER, metavar="ARG")
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return
    if args.command == "check":
        check(args.arguments)
        return
    import_module(COMMANDS[args.command][0]).main(args.arguments)


if __name__ == "__main__":
    main()

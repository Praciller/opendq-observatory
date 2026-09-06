from opendq.__main__ import build_parser


def test_ai_cli_commands_are_bounded_and_explicit() -> None:
    analyze = build_parser().parse_args(["ai", "analyze", "incident-id", "--force"])
    batch = build_parser().parse_args(["ai", "analyze-open", "--limit", "3"])
    pending = build_parser().parse_args(["ai", "pending", "--limit", "5"])

    assert (analyze.command, analyze.ai_command, analyze.force) == ("ai", "analyze", True)
    assert (batch.command, batch.ai_command, batch.limit) == ("ai", "analyze-open", 3)
    assert (pending.command, pending.ai_command, pending.limit) == ("ai", "pending", 5)

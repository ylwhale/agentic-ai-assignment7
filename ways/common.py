"""A helper the ways share: a tool call made by code, traced."""

from harness.client import ToolCall


def code_tool(ctx, step: int, name: str, tool_input: dict) -> str:
    """A tool call made by our code rather than the model, traced like any other."""
    call = ToolCall(id=f"code-{name}-{step}", name=name, input=tool_input)
    result = ctx.tools.call(name, tool_input)
    ctx.trace.tool_call(step, call, result)
    if result.is_error:
        raise RuntimeError(f"{name} failed: {result.content}")
    return result.content


def role_tool(ctx, step: int, role: str, **values) -> str:
    """code_tool for one of RepoMind's roles (tools/roles.yaml): your tool for that role,
    called as its first example calls it, with the role's arguments (the keys, by the
    roles' own names) set to `values`. Since Assignment 3 renamed the tools, the direct
    and workflow ways call them this way; a comment gets Assignment 5's disclosure line,
    as the agent way's do."""
    from harness.scripted import role_call
    if role == "comment":
        from ways.agent import disclosure_line, with_disclosure
        values = {**values, "body": with_disclosure(values.get("body", ""), disclosure_line())}
    name, args = role_call(role, **values)
    return code_tool(ctx, step, name, args)

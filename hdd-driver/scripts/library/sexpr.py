"""Minimal S-expression reader/writer for KiCad files.

Lists are Python lists; atoms are Python str (bare symbols) or Q (quoted
strings); numbers stay as their text form unless written as int/float.
"""
import re


class Q(str):
    """A quoted string atom."""


_TOKEN = re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+)')


def loads(text):
    pos, stack, cur = 0, [], []
    while True:
        m = _TOKEN.match(text, pos)
        if not m:
            break
        tok = m.group(1)
        pos = m.end()
        if tok == "(":
            stack.append(cur)
            cur = []
        elif tok == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif tok.startswith('"'):
            cur.append(Q(re.sub(r'\\(.)', lambda m: {"n": "\n", "t": "\t"}.get(m[1], m[1]), tok[1:-1])))
        else:
            cur.append(tok)
    return cur[0] if len(cur) == 1 else cur


def _atom(a):
    if isinstance(a, Q):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t") + '"'
    if isinstance(a, bool):
        return "yes" if a else "no"
    if isinstance(a, float):
        s = f"{a:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(a)


def dumps(node, indent=0):
    """Write in KiCad's style: one list per line, short leaf lists inline."""
    if not isinstance(node, list):
        return _atom(node)
    simple = all(not isinstance(x, list) for x in node)
    if simple:
        return "(" + " ".join(_atom(x) for x in node) + ")"
    head = [x for x in node if not isinstance(x, list)]
    out = "(" + " ".join(_atom(x) for x in head)
    for x in node:
        if isinstance(x, list):
            out += "\n" + "\t" * (indent + 1) + dumps(x, indent + 1)
    return out + "\n" + "\t" * indent + ")"


def find(node, key):
    """First child list whose head is key."""
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def find_all(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]

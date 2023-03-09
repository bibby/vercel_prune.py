#!/usr/bin/env python
"""
A one-off script to clean up old vercel deployments.
Script assumes that you have the vercel-cli and that it is "switched"
to the team owning the project in question.

vercel-cli should already be "team switched", ie:
$ vercel teams switch my_team_name

configuration:
  set the values for PROJECT and AGE as desired.

use:
  # 1) list deployments without destroying.
  $ ./vercel_prune.py

  # 2) destroy deployments older than AGE
  $ ./vercel_prune.py remove

warning:
  The vercel API will fail at random times with some regularilty.
  It's not your fault. You may repeat the operation.
"""
import sys
import re
import ast
import operator as op
from subprocess import Popen, PIPE

# edit as needed
PROJECT = 'that-project'
AGE = "14d"

# destruction safety; user must be explicit
REMOVE = len(sys.argv) > 1 and sys.argv[1] == "remove"


def markable(d):
    return d.older_than(AGE) or not d.is_state(DeployState.READY)


operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.BitXor: op.xor,
    ast.USub: op.neg
}


class DeployState:
    READY = "READY"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class Deployment:
    def __init__(self, project, domain, state, age, username):
        self.project = project
        self.domain = domain
        self.state = state
        self.age = age
        self.username = username
        self.age_int = parse_age(age)

    def older_than(self, age):
        if isinstance(age, str):
            age = parse_age(age)

        if not all([self.age_int, age]):
            return False

        return self.age_int >= age

    def is_state(self, state):
        return self.state == state

    def __str__(self):
        return "\t".join(map(str, [
            self.domain,
            self.state,
            self.age,
            self.age_int
        ]))


def cmd(*args):
    args = list(map(str, ['vercel'] + list(args)))
    sys.stderr.write(' '.join(args) + "\n")

    p = Popen(args, stdout=PIPE, stderr=PIPE)
    (out, err) = p.communicate()
    return (out.decode("utf-8"),
            err.decode("utf-8"))


def ls_all(project):
    rows = []
    next_ts = None

    while next_ts is not False:
        (deploys, err) = ls(project, next_ts)
        if isinstance(err, dict):
            next_ts = err.get("next", False)
        else:
            next_ts = False
        if not deploys or not len(deploys):
            next_ts = False

        rows = rows + deploys

    return rows


def ls(project, next=None):
    args = ["ls", project]
    if next:
        args = args + ["--next", next]
    (out, err) = cmd(*args)

    return (handle_ls_result(out),
            handle_ls_stderr(err))


def handle_ls_result(raw_out):
    rows = raw_out.split("\n")
    _head = rows.pop(0)
    ret = []
    for row in rows:
        row = row.strip()
        if row:
            fields = re.split('\\s{2,}', row)
            ret.append(Deployment(*fields))
    return ret


def handle_ls_stderr(err):
    for line in err.split("\n"):
        m = re.search('--next (\\d+)', line)
        if m:
            return dict(next=m.group(1))


def remove(deployment):
    if not isinstance(deployment, Deployment):
        raise TypeError("remove() uses a Deployment to keep you from destroying your entire project")
    args = ["remove", "--yes", deployment.domain]
    return cmd(*args)


def eval_expr(expr):
    return eval_(ast.parse(expr, mode='eval').body)


def eval_(node):
    if isinstance(node, ast.Num): # <number>
        return node.n
    elif isinstance(node, ast.BinOp): # <left> <operator> <right>
        return operators[type(node.op)](eval_(node.left), eval_(node.right))
    elif isinstance(node, ast.UnaryOp): # <operator> <operand> e.g., -1
        return operators[type(node.op)](eval_(node.operand))
    else:
        raise TypeError(node)


def _replace(pat, rep, val):
    altered = re.sub(pat, rep, val)
    return altered, altered != val


def parse_age(age):
    patterns = [
        ('m$', ' * 60'),
        ('h$', ' * 3600'),
        ('d$', ' * 86400')
    ]

    for pat, rep in patterns:
        (age, changed) = _replace(pat, rep, age)
        if changed:
            return eval_expr(age)
    return None


if __name__ == '__main__':
    deploys = ls_all(PROJECT)
    to_remove = []

    print("{} Deployments".format(len(deploys)))

    print("------------")
    for d in deploys:
        print(d)
        if markable(d):
            to_remove.append(d)

    print("{} to remove".format(len(to_remove)))
    if not REMOVE:
        exit(0)

    while len(to_remove):
        print("\n\n----------")
        print("{} to remove".format(len(to_remove)))
        (out, err) = remove(to_remove.pop(0))
        print("----STDOUT-----")
        print(out)
        print("----STDERR-----")
        print(err)

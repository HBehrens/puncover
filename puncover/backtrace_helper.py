import re

from puncover import collector


class BacktraceHelper:
    def __init__(self, collector):
        self.collector = collector
        # Memo for deepest-tree results, kept OFF the symbol dicts on purpose:
        # only acyclic (path-independent) results are stored here, so nothing
        # cached is ever a cyclic, order-dependent value that could be wrongly
        # reused for another start node.
        self._deepest_memo = {}

    derive_functions_symbols_pattern = re.compile(r"\b(\w+)\b")

    def derive_function_symbols(self, text):
        result = []
        for f in self.derive_functions_symbols_pattern.finditer(text):
            s = self.collector.symbol(f.group(1), False)
            if s and s[collector.TYPE] == collector.TYPE_FUNCTION:
                result.append(s)
        return result

    def transform_known_symbols(self, text, transformer):
        def f(match):
            symbol_name = match.group(1)
            symbol = self.collector.symbol(symbol_name, False)
            return transformer(symbol) if symbol else symbol_name

        return self.derive_functions_symbols_pattern.sub(f, text)

    def deepest_call_tree(self, f, list_attribute, cache_attribute, visited=None):
        result, _ = self._deepest_call_tree(f, list_attribute, cache_attribute, visited)
        return result

    def _deepest_call_tree(self, f, list_attribute, cache_attribute, visited=None):
        # Returns (result, hit_cycle). The deepest call tree is the longest
        # *simple* path (each function counted once); cycles are broken via the
        # `visited` set.
        #
        # `hit_cycle` is True when a back-edge to a node already on the current
        # path had to be dropped. Such a result is PATH-DEPENDENT, so it must not
        # be memoized: caching it under one start node and reusing it from another
        # is exactly what produced order-dependent, under-counted worst-case
        # stacks (e.g. a function inside a mutual-recursion cycle reporting only
        # its own frame). Acyclic results do not depend on the path, so they are
        # cached as before and the traversal stays fast on the common case.
        memo_key = (id(f), cache_attribute)
        if memo_key in self._deepest_memo:
            return self._deepest_memo[memo_key], False

        visited = [f] + (visited if visited else [])
        result = (0, [])
        hit_cycle = False

        for c in f[list_attribute]:
            if c in visited:
                hit_cycle = True
                continue
            candidate, child_hit_cycle = self._deepest_call_tree(
                c, list_attribute, cache_attribute, visited
            )
            hit_cycle = hit_cycle or child_hit_cycle
            if candidate[0] > result[0]:
                result = candidate

        result = (result[0] + f.get(collector.STACK_SIZE, 0), [f] + result[1])
        if not hit_cycle:
            self._deepest_memo[memo_key] = result
        return result, hit_cycle

    def annotate_call_tree_flags(self):
        """Set the per-function call-tree warning flags: how many functions
        anywhere in the call tree perform an indirect call, lack a stack size, or
        have a dynamic stack frame, plus a recursion flag. The tree is the union
        of everything reachable via callees and via callers (the worst-case page
        shows both directions), deduplicated, so a problem deep in the tree warns
        every ancestor -- not just the direct parent.

        Kept out of the memoised deepest_call_tree on purpose: cyclic results are
        intentionally not cached there, so counting during that traversal would
        double-count on re-expansion. This pass is order-independent.
        """
        callee_recursion = {}
        caller_recursion = {}
        for f in self.collector.all_functions():
            tree = {}
            tree.update(self._reachable(f, collector.CALLEES))
            tree.update(self._reachable(f, collector.CALLERS))
            functions = tree.values()
            unresolved = sum(1 for c in functions if c.get(collector.PERFORMS_INDIRECT_CALL))
            missing = sum(1 for c in functions if collector.STACK_SIZE not in c)
            unbound = sum(1 for c in functions if c.get(collector.STACK_QUALIFIERS) == "dynamic")
            if unresolved:
                f[collector.UNRESOLVED_CALLS_IN_CALL_TREE] = unresolved
            if missing:
                f[collector.MISSING_STACKSIZE_IN_CALL_TREE] = missing
            if unbound:
                f[collector.UNBOUND_STACKSIZE_IN_CALL_TREE] = unbound
            # A call tree that contains recursion (direct self-calls or a mutual
            # cycle) cannot have its stack bounded statically, so flag it -- the
            # deepest-path figure is then a lower bound, not an upper bound.
            if self._reaches_recursion(
                f, collector.CALLEES, callee_recursion
            ) or self._reaches_recursion(f, collector.CALLERS, caller_recursion):
                f[collector.RECURSION_IN_CALL_TREE] = True

    def _reachable(self, f, list_attribute):
        """All functions reachable from f along ``list_attribute`` (its whole
        callee- or caller-tree), as an ``{id: function}`` map. f itself is
        included only if it lies on a cycle. Iterative, cycle-safe BFS."""
        seen = {}
        stack = list(f.get(list_attribute, []))
        while stack:
            c = stack.pop()
            cid = id(c)
            if cid in seen:
                continue
            seen[cid] = c
            stack.extend(c.get(list_attribute, []))
        return seen

    def _reaches_recursion(self, f, list_attribute, memo, on_stack=None):
        """Whether f -- or anything reachable along ``list_attribute`` -- lies on
        a cycle (mutual recursion) or is directly self-recursive. Unlike the
        deepest path, "reaches a cycle" does not depend on how f was reached, so
        it is safe to memoise across start nodes."""
        key = id(f)
        if key in memo:
            return memo[key]
        if f.get(collector.SELF_RECURSIVE):
            memo[key] = True
            return True
        if on_stack is None:
            on_stack = set()
        on_stack.add(key)
        result = False
        for c in f[list_attribute]:
            ck = id(c)
            if (
                ck in on_stack
                or memo.get(ck)
                or self._reaches_recursion(c, list_attribute, memo, on_stack)
            ):
                result = True
                break
        on_stack.discard(key)
        memo[key] = result
        return result

    def deepest_callee_tree(self, f):
        result = self.deepest_call_tree(f, collector.CALLEES, collector.DEEPEST_CALLEE_TREE)
        # Always expose the deepest tree on the symbol, even when it contains a
        # cycle: the template and the report read this key unconditionally.
        f[collector.DEEPEST_CALLEE_TREE] = result
        return result

    def deepest_caller_tree(self, f):
        result = self.deepest_call_tree(f, collector.CALLERS, collector.DEEPEST_CALLER_TREE)
        f[collector.DEEPEST_CALLER_TREE] = result
        return result

"""Граф зависимостей: построение обходом в глубину (DFS, рекурсивно)."""


class GraphError(Exception):
    """Ошибка построения графа."""


class DependencyGraph:
    """Рёбра графа (пакет -> зависимости), циклы и исключённые пакеты."""

    def __init__(self):
        """Создаёт пустой граф."""
        self.edges = {}
        self.cycles = []
        self.skipped = []

    def edge_count(self):
        """Общее число рёбер."""
        return sum(len(deps) for deps in self.edges.values())


def is_skipped(name, substring):
    """Пакет исключается, если его имя содержит подстроку фильтра."""
    return bool(substring) and substring in name


def visit(repo, node, substring, graph, path):
    """Рекурсивный DFS: path - текущий путь от корня (для поиска циклов)."""
    graph.edges[node] = []
    path.append(node)
    for dep in dict.fromkeys(repo.dependencies(node)):
        if is_skipped(dep, substring):
            if dep not in graph.skipped:
                graph.skipped.append(dep)
            continue
        graph.edges[node].append(dep)
        if dep in path:
            graph.cycles.append(path[path.index(dep):] + [dep])
        elif dep not in graph.edges:
            visit(repo, dep, substring, graph, path)
    path.pop()


def build_graph(repo, root, substring="", graph=None):
    """Строит граф зависимостей пакета root (с учётом транзитивности)."""
    if is_skipped(root, substring):
        raise GraphError(
            f"корневой пакет '{root}' исключён фильтром '{substring}'")
    graph = graph if graph is not None else DependencyGraph()
    if root in graph.edges:
        return graph
    try:
        visit(repo, root, substring, graph, [])
    except RecursionError:
        raise GraphError(
            "граф слишком глубокий для рекурсивного обхода") from None
    return graph


def describe_cycles(graph):
    """Строки отчёта о циклических зависимостях."""
    if not graph.cycles:
        return ["Циклических зависимостей не найдено."]
    lines = ["Циклические зависимости:"]
    lines.extend("  " + " -> ".join(cycle) for cycle in graph.cycles)
    return lines


def describe(graph, root):
    """Текстовый отчёт: рёбра графа, циклы, исключённые пакеты."""
    lines = [f"Граф зависимостей пакета {root}: "
             f"вершин {len(graph.edges)}, рёбер {graph.edge_count()}"]
    for node, deps in graph.edges.items():
        targets = ", ".join(deps) if deps else "(нет зависимостей)"
        lines.append(f"  {node} -> {targets}")
    lines.extend(describe_cycles(graph))
    if graph.skipped:
        lines.append("Исключены фильтром: " + ", ".join(graph.skipped))
    return "\n".join(lines)


class ReverseRepository:
    """Репозиторий-адаптер: зависимости пакета = пакеты, зависящие от него."""

    def __init__(self, dependents):
        """Принимает словарь {пакет: список зависящих от него пакетов}."""
        self.dependents = dependents

    def dependencies(self, name):
        """Пакеты, которые зависят от name."""
        return self.dependents.get(name, [])


def build_full_graph(repo, roots, substring=""):
    """Общий граф всех пакетов, достижимых из roots (DFS из каждого)."""
    graph = DependencyGraph()
    for root in roots:
        if not is_skipped(root, substring):
            build_graph(repo, root, substring, graph)
    return graph


def invert(graph):
    """Обращает рёбра: {пакет: список пакетов, зависящих от него}."""
    dependents = {}
    for node, deps in graph.edges.items():
        for dep in deps:
            dependents.setdefault(dep, []).append(node)
    return dependents


def reverse_graph(graph, target):
    """Обратные зависимости target тем же обходом DFS по обращённым рёбрам."""
    if target not in graph.edges:
        raise GraphError(f"пакет '{target}' отсутствует в анализируемом графе")
    return build_graph(ReverseRepository(invert(graph)), target)


def describe_reverse(graph, target):
    """Текстовый отчёт об обратных зависимостях пакета."""
    count = len(graph.edges) - 1
    lines = [f"Обратные зависимости пакета {target} "
             f"(пакеты, зависящие от него): {count}"]
    for node, dependents in graph.edges.items():
        sources = ", ".join(dependents) or "(никто не зависит)"
        lines.append(f"  {node} <- {sources}")
    lines.extend(describe_cycles(graph))
    return "\n".join(lines)

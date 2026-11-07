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

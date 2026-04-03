from typing import Any


class DAGEngine:
    def get_unlocked(self, nodes: list[dict], completed: set[str]) -> list[dict]:
        """返回所有前置条件已满足的未完成节点"""
        result = []
        for node in nodes:
            if node["id"] in completed:
                continue
            if all(p in completed for p in node.get("prerequisites", [])):
                result.append(node)
        return result

    def has_cycle(self, edges: dict[str, list[str]]) -> bool:
        """检测 DAG 中是否有环"""
        visited = set()
        rec_stack = set()

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in edges.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in edges:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def all_reachable(self, start: str, edges: dict[str, list[str]], total_nodes: int) -> bool:
        """检查从 start 是否能到达所有节点"""
        visited = set()

        def dfs(node):
            visited.add(node)
            for neighbor in edges.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)

        dfs(start)
        return len(visited) == total_nodes

    def get_learning_path(self, start: str, edges: dict[str, list[str]]) -> list[str]:
        """获取学习路径（拓扑排序，BFS-like 保证依赖在前）"""
        # Build in-degree map from edges
        in_degree: dict[str, int] = {start: 0}
        for node, neighbors in edges.items():
            if node not in in_degree:
                in_degree[node] = 0
            for neighbor in neighbors:
                if neighbor not in in_degree:
                    in_degree[neighbor] = 0
                in_degree[neighbor] += 1

        # BFS topological sort starting from 'start'
        from collections import deque
        queue = deque([start])
        path = []
        visited = set()

        while queue:
            node = queue.popleft()
            if node in visited:
                # Decrement in-degree and check if ready
                continue
            # Only process when in-degree is effectively 0 relative to visited nodes
            # Since we start from 'start', and only enqueue neighbors after visiting parents,
            # we track visited to avoid re-processing
            visited.add(node)
            path.append(node)
            for neighbor in edges.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return path

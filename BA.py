from manim import *
import networkx as nx
import random

class BANetworkAnimation(Scene):
    def construct(self):
        # ======================
        # BA 模型参数
        # ======================
        total_nodes = 16  # 总节点数（适当减少）
        m0 = 3            # 初始节点数
        m = 2             # 每个新节点固定连边数

        # 初始化 BA 网络
        G = nx.Graph()
        G.add_nodes_from(range(m0))
        for i in range(m0):
            for j in range(i + 1, m0):
                G.add_edge(i, j)

        base_radius = 0.2 * 1.1

        def _enforce_min_distance(pos_map, min_dist=0.72, iterations=36):
            nodes = list(pos_map.keys())
            for _ in range(iterations):
                moved = False
                for i in range(len(nodes)):
                    a = nodes[i]
                    for j in range(i + 1, len(nodes)):
                        b = nodes[j]
                        delta = pos_map[b] - pos_map[a]
                        dist = np.linalg.norm(delta[:2])
                        if dist < 1e-6:
                            ang = random.uniform(0, TAU)
                            direction = np.array([np.cos(ang), np.sin(ang), 0.0])
                            push = 0.5 * min_dist * direction
                            pos_map[a] = pos_map[a] - push
                            pos_map[b] = pos_map[b] + push
                            moved = True
                        elif dist < min_dist:
                            direction = delta / dist
                            push = 0.5 * (min_dist - dist) * direction
                            pos_map[a] = pos_map[a] - push
                            pos_map[b] = pos_map[b] + push
                            moved = True
                if not moved:
                    break
            return pos_map

        def _spring_positions(scale=2.7):
            pos_2d = nx.spring_layout(G, seed=42, k=1.3 / np.sqrt(len(G.nodes())))
            pos_map = {
                node: np.array([xy[0] * scale, xy[1] * scale, 0.0])
                for node, xy in pos_2d.items()
            }
            return _enforce_min_distance(pos_map, min_dist=0.72)

        # ======================
        # Manim 网络图布局（初始使用 spring）
        # ======================
        graph = Graph(
            vertices=list(G.nodes),
            edges=list(G.edges),
            layout=_spring_positions(),
            vertex_config={"radius": 0.2, "fill_color": LIGHT_GRAY},
            edge_config={"stroke_color": GRAY}
        )
        graph.scale(1.1)
        title = Text("BA model: preferential attachment", font_size=30).to_edge(UP)
        hint = Text("new node picks targets with probability proportional to degree", font_size=20)
        hint.next_to(title, DOWN, buff=0.12)
        self.play(Create(graph), run_time=1.5)
        self.play(FadeIn(title), FadeIn(hint), run_time=0.7)
        self.wait(0.5)

        def _to_mobject_list(obj):
            if isinstance(obj, dict):
                return list(obj.values())
            if isinstance(obj, (list, tuple, set)):
                return list(obj)
            return [obj]

        def _animate_layout_reflow(run_time=0.6):
            pos = _spring_positions()
            self.play(graph.animate.change_layout(pos), run_time=run_time)

        node_scale = {n: 1.0 for n in G.nodes()}

        def _animate_degree_size(run_time=0.35):
            min_scale = 0.72
            max_scale = 1.65
            deg_map = {n: G.degree(n) for n in G.nodes()}
            d_min = min(deg_map.values())
            d_max = max(deg_map.values())

            animations = []
            for node in G.nodes():
                if d_max == d_min:
                    target = 1.0
                else:
                    ratio = (deg_map[node] - d_min) / (d_max - d_min)
                    target = min_scale + (max_scale - min_scale) * ratio

                base = node_scale.get(node, 1.0)
                factor = target / base if base != 0 else 1.0
                node_scale[node] = target
                animations.append(graph.vertices[node].animate.scale(factor))

            if animations:
                self.play(*animations, run_time=run_time)

        def _has_visible_overlap(padding=1.06):
            nodes = list(graph.vertices.keys())
            for i in range(len(nodes)):
                a = nodes[i]
                ca = graph.vertices[a].get_center()
                for j in range(i + 1, len(nodes)):
                    b = nodes[j]
                    cb = graph.vertices[b].get_center()
                    dist = np.linalg.norm((ca - cb)[:2])
                    need = base_radius * (node_scale.get(a, 1.0) + node_scale.get(b, 1.0)) * padding
                    if dist < need:
                        return True
            return False

        def _pick_spawn_position(targets, new_node):
            target_centers = [graph.vertices[t].get_center() for t in targets]
            spawn_center = np.mean(target_centers, axis=0)
            existing = [mob.get_center() for mob in graph.vertices.values()]
            min_gap = 0.8
            angle_offset = TAU * (new_node - m0 + 1) / max(1, (total_nodes - m0))

            best_pos = spawn_center + 0.95 * RIGHT
            best_score = -1.0
            for radius in [0.55, 0.75, 0.95, 1.15, 1.35]:
                for k in range(24):
                    angle = angle_offset + TAU * k / 24
                    candidate = spawn_center + radius * (
                        np.cos(angle) * RIGHT + np.sin(angle) * UP
                    )
                    nearest = min(np.linalg.norm((candidate - p)[:2]) for p in existing)
                    if nearest > best_score:
                        best_score = nearest
                        best_pos = candidate
                    if nearest >= min_gap:
                        return candidate
            return best_pos

        def _update_top3_highlight(run_time=0.35):
            top_nodes = sorted(G.nodes(), key=lambda x: G.degree(x), reverse=True)[:3]
            top_colors = [RED, ORANGE, GOLD]
            self.play(
                *[graph.vertices[node].animate.set_fill(LIGHT_GRAY) for node in G.nodes()],
                *[
                    graph.vertices[node].animate.set_fill(color)
                    for node, color in zip(top_nodes, top_colors)
                ],
                run_time=run_time,
            )
            self.play(
                *[
                    Indicate(graph.vertices[node], color=color, scale_factor=1.28)
                    for node, color in zip(top_nodes, top_colors)
                ],
                run_time=0.45,
            )

        _animate_degree_size(run_time=0.4)
        _update_top3_highlight(run_time=0.3)

        # ======================
        # 逐一生成新节点（BA生长动画）
        # ======================
        for new_node in range(m0, total_nodes):
            # 优先连接概率计算
            degrees = [G.degree(n) for n in G.nodes()]
            total_deg = sum(degrees)

            # 选择固定的 m 个目标节点（按度数加权）
            targets = []
            while len(targets) < m:
                r = random.uniform(0, total_deg)
                acc = 0
                for idx, k in enumerate(degrees):
                    acc += k
                    if acc >= r and idx not in targets:
                        targets.append(idx)
                        break

            self.play(
                *[Indicate(graph.vertices[t], color=YELLOW, scale_factor=1.35) for t in targets],
                run_time=0.55,
            )

            # 添加节点与边到网络
            G.add_node(new_node)
            new_edges = [(new_node, t) for t in targets]
            G.add_edges_from(new_edges)

            # ======================
            # Manim 动画：添加节点 + 连线
            # ======================
            new_pos = _pick_spawn_position(targets, new_node)
            new_vertex_mobjects = _to_mobject_list(
                graph.add_vertices(new_node, positions={new_node: new_pos})
            )
            self.play(*[FadeIn(mob) for mob in new_vertex_mobjects], run_time=0.8)

            new_edge_mobjects = _to_mobject_list(graph.add_edges(*new_edges))
            for mob in new_edge_mobjects:
                mob.set_stroke(YELLOW, width=4)
            self.play(*[Create(mob) for mob in new_edge_mobjects], run_time=0.7)
            self.play(*[mob.animate.set_stroke(GRAY, width=2.5) for mob in new_edge_mobjects], run_time=0.25)

            node_scale[new_node] = 1.0
            _animate_degree_size(run_time=0.3)
            _update_top3_highlight(run_time=0.3)

            if _has_visible_overlap():
                _animate_layout_reflow(run_time=0.32)

            # 每 3 轮做一次 spring 重排，减少画面抖动
            round_index = new_node - m0 + 1
            if round_index % 3 == 0:
                _animate_layout_reflow(run_time=0.5)
            self.wait(0.12)

        self.wait(3)
class TributeEngine:
    def build_node_tribute(self, node_id: str, node_title: str, contributor: dict) -> str:
        name = contributor.get("name", "匿名")
        quote = contributor.get("quote", "")
        github = contributor.get("github", "")
        lines = [
            f'⭐ {node_title} 由 **{name}** 点亮',
            "",
        ]
        if quote:
            lines.append(f'> "{quote}"')
            lines.append("")
        if github:
            lines.append(f"感谢 @{github} 让这段知识得以存在。")
        else:
            lines.append(f"感谢 {name} 让这段知识得以存在。")
        return "\n".join(lines)

    def build_completion_tribute(self, cartridge_id: str, title: str, contributors: list[dict], learner_count: int = 0) -> str:
        lines = [
            f"🎓 恭喜通关「{title}」！",
            "",
        ]
        if learner_count > 0:
            lines.append(f"你是第 {learner_count} 位点亮这颗星的人 ✨")
            lines.append("")

        if contributors:
            lines.append("## 贡献者")
            lines.append("")
            for c in contributors:
                name = c.get("name", "匿名")
                role = c.get("role", "")
                quote = c.get("quote", "")
                role_label = {"author": "作者", "reviewer": "审阅者", "maintainer": "维护者"}.get(role, role)
                line = f"- **{name}**（{role_label}）"
                if quote:
                    line += f' _"{quote}"_'
                lines.append(line)
        return "\n".join(lines)

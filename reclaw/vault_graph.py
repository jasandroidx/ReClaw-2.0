"""
Ravenstack Obsidian Vault Graph Engine
Parses wikilinks, frontmatter, and tags across the Obsidian vault
to provide fast BFS, shortest path, and relationship lookups.
"""

import re
from pathlib import Path
from collections import deque
from typing import Dict, List, Set, Optional, Any


class VaultGraph:
    def __init__(self, vault_path: str = "/root/obsidian-vault/Ravenstack"):
        self.vault_path = Path(vault_path)
        self.nodes: Set[str] = set()
        self.edges: Dict[str, Set[str]] = {}           # Outgoing links
        self.reverse_edges: Dict[str, Set[str]] = {}   # Backlinks
        self.tags: Dict[str, Set[str]] = {}            # Node -> tags
        self.file_map: Dict[str, Path] = {}            # Node name -> file path
        self.rebuild()

    def _normalize_name(self, name: str) -> str:
        """Strip extension and path prefixes to get clean node name."""
        clean = Path(name).stem.strip()
        return clean

    def rebuild(self) -> Dict[str, int]:
        """Scans the vault directory and builds the graph in memory."""
        self.nodes.clear()
        self.edges.clear()
        self.reverse_edges.clear()
        self.tags.clear()
        self.file_map.clear()

        if not self.vault_path.exists():
            return {"nodes": 0, "edges": 0}

        wikilink_pattern = re.compile(r"\[\[(.*?)\]\]")
        frontmatter_tag_pattern = re.compile(r"^tags:\s*\[?(.*?)\]?$", re.MULTILINE)

        # First pass: register all markdown files as nodes
        for md_file in self.vault_path.rglob("*.md"):
            node_name = self._normalize_name(md_file.name)
            self.nodes.add(node_name)
            self.file_map[node_name] = md_file
            self.edges[node_name] = set()
            self.reverse_edges[node_name] = set()
            self.tags[node_name] = set()

        total_edges = 0

        # Second pass: parse links and frontmatter
        for node_name, md_file in self.file_map.items():
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Extract tags from frontmatter
            fm_match = frontmatter_tag_pattern.search(content)
            if fm_match:
                raw_tags = fm_match.group(1).replace('"', '').replace("'", '')
                for t in raw_tags.split(","):
                    tag_clean = t.strip().lstrip("#")
                    if tag_clean:
                        self.tags[node_name].add(tag_clean)

            # Extract wikilinks: [[Target]] or [[Target|Alias]]
            links = wikilink_pattern.findall(content)
            for raw_link in links:
                target = raw_link.split("|")[0].split("#")[0].strip()
                target_name = self._normalize_name(target)
                
                if not target_name:
                    continue

                # Add target node if it doesn't exist as a physical file yet
                if target_name not in self.nodes:
                    self.nodes.add(target_name)
                    self.edges[target_name] = set()
                    self.reverse_edges[target_name] = set()
                    self.tags[target_name] = set()

                self.edges[node_name].add(target_name)
                self.reverse_edges[target_name].add(node_name)
                total_edges += 1

        return {"nodes": len(self.nodes), "edges": total_edges}

    def find_shortest_path(self, start: str, target: str) -> Optional[List[str]]:
        """BFS to find the shortest connection chain between two notes."""
        start_node = self._normalize_name(start)
        target_node = self._normalize_name(target)

        if start_node not in self.nodes or target_node not in self.nodes:
            return None

        if start_node == target_node:
            return [start_node]

        queue = deque([[start_node]])
        visited = {start_node}

        while queue:
            path = queue.popleft()
            curr = path[-1]

            neighbors = self.edges.get(curr, set()) | self.reverse_edges.get(curr, set())

            for neighbor in neighbors:
                if neighbor == target_node:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])

        return None

    def get_neighborhood(self, node: str, depth: int = 1) -> Dict[str, Any]:
        """Returns local graph neighbors, backlinks, and tags up to depth N."""
        center = self._normalize_name(node)
        if center not in self.nodes:
            return {"error": f"Node '{node}' not found in vault graph."}

        results = {
            "node": center,
            "exists_on_disk": center in self.file_map,
            "tags": list(self.tags.get(center, set())),
            "outbound_links": list(self.edges.get(center, set())),
            "backlinks": list(self.reverse_edges.get(center, set()))
        }

        if depth > 1:
            extended_network = set()
            for outbound in results["outbound_links"]:
                extended_network.update(self.edges.get(outbound, set()))
            for backlink in results["backlinks"]:
                extended_network.update(self.reverse_edges.get(backlink, set()))
            extended_network.discard(center)
            results["depth_2_connections"] = list(extended_network)

        return results

    def get_top_hubs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns the most connected notes (highest degree centrality)."""
        scored = []
        for node in self.nodes:
            in_deg = len(self.reverse_edges.get(node, set()))
            out_deg = len(self.edges.get(node, set()))
            total = in_deg + out_deg
            scored.append({
                "node": node,
                "total_connections": total,
                "backlinks": in_deg,
                "outbound": out_deg,
                "exists_on_disk": node in self.file_map
            })
        
        scored.sort(key=lambda x: x["total_connections"], reverse=True)
        return scored[:limit]

    def find_orphans(self) -> List[str]:
        """Finds notes that have zero incoming and zero outgoing links."""
        orphans = []
        for node in self.file_map:
            if not self.edges.get(node) and not self.reverse_edges.get(node):
                orphans.append(node)
        return sorted(orphans)

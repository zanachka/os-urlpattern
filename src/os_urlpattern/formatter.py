"""Clustered record formatter.
"""
import json
from collections import OrderedDict

from .definition import BasePatternRule, Symbols
from .parse_utils import pack
from .utils import dump_tree


class Formatter(object):
    """Base class for clustered data formatter.

    The subclass must define format method, which yield formatted string.
    """

    def format(self, url_meta, root, **kwargs):
        """Format the clustered tree.

        Args:
            url_meta (URLMeta): The url_meta.
            root (TreeNode): Root node of the clustered tree.
            **kwargs: Arbitray keyword arguments.

        Yields:
            str: the formatted string.

        """
        return
        yield


class PatternFormatter(Formatter):
    """Pattern only formatter."""

    def format(self, url_meta, root, **kwargs):
        """Generate url pattern string.

        Args:
            url_meta (URLMeta): The URLMeta object.
            root (TreeNode): Root of a clustered piece tree.
            **kwargs: Arbitray keyword arguments.

        Yields:
            str: URL pattern string.

        """
        for nodes in dump_tree(root):
            yield pack(url_meta, [p.pattern for p in nodes[1:]])
            break


class ClusterFormatter(PatternFormatter):
    """Pattern and meta data formatter."""

    def format(self, url_meta, root, **kwargs):
        """Generate url pattern string and dumps bound meta data.

        Args:
            url_meta (URLMeta): The URLMeta object.
            root (TreeNode): Root of a clustered piece tree.
            **kwargs: Arbitray keyword arguments.

        Yields:
            str: Yield URL pattern string first, then yield meta
                data of this cluster.

        """
        for r in super(ClusterFormatter, self).format(url_meta, root, **kwargs):
            yield r

        for nodes in dump_tree(root):
            for url in nodes[-1].meta:
                yield u'\t'.join((u'', url))


class JsonFormatter(Formatter):
    """Json record of pattern info formatter."""

    def format(self, url_meta, root, **kwargs):
        """Generate json format of URL pattern and info.

        Args:
            url_meta (URLMeta): The URLMeta object.
            root (TreeNode): Root of a clustered piece tree.
            **kwargs: Arbitray keyword arguments.

        Yields:
            str: Json string, key-value:
                ptn: URL pattern string.
                cnt: Number of uniq path in the cluster.
        """
        for nodes in dump_tree(root):
            p = pack(url_meta, [p.pattern for p in nodes[1:]])
            yield json.dumps({u'ptn': p, u'cnt': root.count})
            break


class ETEFormatter(Formatter):
    """Ete tree formatter."""

    def format(self, url_meta, root, **kwargs):
        """Generate ete tree string.

        Args:
            url_meta (URLMeta): The URLMeta object.
            root (TreeNode): Root of a pattern tree.
            **kwargs: Arbitray keyword arguments.

        Yields:
            str: An ete tree string.
        """
        def f(pattern_node):
            sep = Symbols.EMPTY
            query_key = Symbols.EMPTY
            path_depth = url_meta.path_depth
            query_depth = len(url_meta.query_keys)
            current_level = pattern_node.level
            if path_depth < current_level \
                    and current_level <= (path_depth + query_depth):
                sep = Symbols.AMPERSAND
                if current_level == path_depth + 1:
                    sep = BasePatternRule.SINGLE_QUESTION
                query_key = url_meta.query_keys[current_level - path_depth - 1]
            elif current_level == path_depth + query_depth + 1:
                sep = Symbols.NUMBER
            return u' {sep}{query_key}{pattern_string}({count}) '.format(
                count=pattern_node.count,
                pattern_string=pattern_node.value,
                query_key=query_key,
                sep=sep)

        if root.count <= 0:
            return

        ete_tree = get_ete_tree(root, format=f)
        yield ete_tree.get_ascii(show_internal=True)


def get_ete_tree(root_node, format=str):
    """Transfor a tree-like object into ete tree.

    Args:
        root_node (TreeNode): The root of the tree.
        format (callable, optional): Defaults to str.
            A callable object to format the ete tree node.

    Returns:
        ete3.Tree: The ete tree.
    """
    from ete3 import Tree

    def add_children(node, ete_node):
        for child in node.children:
            ete_child = ete_node.add_child(name=format(child))
            add_children(child, ete_child)

    ete_root_node = Tree(name=format(root_node))
    add_children(root_node, ete_root_node)
    return ete_root_node


FORMATTERS = OrderedDict([
    ('NULL', Formatter()),
    ('PATTERN', PatternFormatter()),
    ('CLUSTER', ClusterFormatter()),
    ('JSON', JsonFormatter()),
])
try:
    import ete3
    FORMATTERS['ETE'] = ETEFormatter()
except:
    pass


def pformat(name, url_meta, root, **kwargs):
    """Shortcut for formatting.

    Args:
        name (str): Format type.
        url_meta (URLMeta): The URLMeta object.
        root (TreeNode): Root of a clustered tree.
        **kwargs: Arbitray keyword arguments.

    Returns:
        Iterator: For iterate formatted strings.
    """
    return FORMATTERS[name.upper()].format(url_meta, root, **kwargs)

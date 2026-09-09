import pytest

from django_div import A, Comment, Div, Fragment, P, Raw, Span, Tag, Text


def test_predicate_search_preserves_order_filters_and_root_exclusion():
    first = A("one", class_="external featured", href="/one")
    second = A("two", class_="external", href="/two")
    tree = Div(Fragment(first), Span(second), class_="external")

    def predicate(node):
        return node.has_class("external")

    assert tree.find(predicate) is first
    assert tree.find_all(predicate) == [first, second]
    assert list(tree.iter_find(predicate, href="/two")) == [second]
    assert tree.find_all("a", class_="external") == [second]
    assert tree.find(predicate, href="/missing") is None
    assert tree.find_all(lambda node: node.tag in {"a", "span"}) == [
        first,
        tree.children[1],
        second,
    ]


def test_predicate_search_is_lazy_and_short_circuits():
    seen = []
    tree = Div(P("one"), P("two"))

    def predicate(node):
        seen.append(node)
        return True

    matches = tree.iter_find(predicate)
    assert seen == []
    assert next(matches) is tree.children[0]
    assert seen == [tree.children[0]]
    seen.clear()
    assert tree.find(predicate) is tree.children[0]
    assert seen == [tree.children[0]]


def test_transform_visits_postorder_and_copies_nodes():
    tree = Div(Fragment(P("old")), Comment(content="note"), Raw(content="<b>x</b>"))
    original_nodes = list(tree.walk())
    seen = []

    def visitor(node):
        assert all(node is not original for original in original_nodes)
        seen.append(type(node))
        if isinstance(node, Text):
            node.content = "new"
        if isinstance(node, Tag):
            node.attrs["title"] = "copied"
        return node

    result = tree.transform(visitor)
    assert seen == [Text, P, Fragment, Comment, Raw, Div]
    assert (
        str(result)
        == '<div title="copied"><p title="copied">new</p><!--note--><b>x</b></div>'
    )
    assert str(tree) == "<div><p>old</p><!--note--><b>x</b></div>"


def test_transform_removes_replaces_and_unwraps():
    tree = Div(P("remove"), Span(P("keep")), P("replace"))
    seen = []

    def visitor(node):
        seen.append(node)
        if isinstance(node, P) and node.text == "remove":
            return None
        if isinstance(node, Span):
            return Fragment(node.children)
        if isinstance(node, P) and node.text == "replace":
            return Fragment(P("new one"), P("new two"))
        return node

    result = tree.transform(visitor)
    assert str(result) == "<div><p>keep</p><p>new one</p><p>new two</p></div>"
    assert all(
        not isinstance(node, P) or not node.text.startswith("new") for node in seen
    )
    assert str(tree) == "<div><p>remove</p><span><p>keep</p></span><p>replace</p></div>"
    assert str(Tag.model_validate_json(result.model_dump_json())) == str(result)


def test_transform_root_leaf_and_empty_fragment():
    assert P("hello").transform(lambda node: None) is None
    assert (
        str(Text(content="hello").transform(lambda node: P(node.content)))
        == "<p>hello</p>"
    )
    empty = Fragment()
    copy = empty.transform(lambda node: node)
    assert isinstance(copy, Fragment)
    assert copy is not empty
    assert copy.children is not empty.children


def test_transform_shared_occurrences_are_independent_and_attrs_shallow():
    shared = P("hello", style={"color": "red"})
    tree = Div(shared, shared)
    result = tree.transform(lambda node: node)
    first, second = result.children
    assert first is not second and first is not shared
    assert first.children[0] is not second.children[0]
    assert first.attrs is not shared.attrs
    assert first.attrs["style"] is shared.attrs["style"]


def test_transform_handles_deep_trees():
    tree = current = Div()
    for _ in range(3000):
        child = Div()
        current.children.append(child)
        current = child
    result = tree.transform(lambda node: node)
    assert str(result) == str(tree)
    assert len(list(result.walk())) == 3001


def test_transform_rejects_invalid_results_and_preserves_source_on_error():
    tree = Div(P("hello"))
    with pytest.raises(TypeError, match="HtmlItem or None"):
        tree.transform(lambda node: "not a node")

    def visitor(node):
        if isinstance(node, P):
            node.attrs["title"] = "copied"
        if isinstance(node, Div):
            raise RuntimeError("stop")
        return node

    with pytest.raises(RuntimeError, match="stop"):
        tree.transform(visitor)
    assert str(tree) == "<div><p>hello</p></div>"

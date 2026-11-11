"""Tests for the screen/form/field analyzer (BEAN-064)."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.screens import (
    analyze_screens,
    map_screen_fields,
)
from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    ModelField,
    ModelSurface,
    RouteSurface,
    SourceRef,
)
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult


def _inv(paths: list[str]) -> InventoryResult:
    files = [
        FileEntry(
            path=p,
            size=1,
            extension="." + p.rsplit(".", 1)[-1],
            hash="h",
            category="source",
        )
        for p in paths
    ]
    return InventoryResult(
        files=files, skipped=[], total_files=len(files), total_size=1, total_skipped=0
    )


def _run(tmp_path: Path, files: dict[str, str], **kw):  # type: ignore[no-untyped-def]
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return analyze_screens(tmp_path, _inv(list(files)), **kw)


def test_react_controlled_form_with_zod_resolver_and_html_attrs(tmp_path: Path) -> None:
    code = """
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
const Schema = z.object({ title: z.string().min(3), qty: z.number() });
export default function OrderForm() {
  const form = useForm({ resolver: zodResolver(Schema) });
  return (
    <form onSubmit={form.handleSubmit(save)}>
      <label htmlFor="t">Title</label>
      <input id="t" {...form.register("title")} />
      <input type="number" name="qty" min={1} max="9" required />
      <select name="kind"><option>a</option></select>
      <textarea name="notes" />
      <input type="hidden" name="csrf" />
      <button type="submit">Go</button>
    </form>
  );
}
"""
    (screen,) = _run(tmp_path, {"OrderForm.tsx": code})
    f = {x.name: x for x in screen.fields}
    assert set(f) == {"title", "qty", "kind", "notes"}
    assert f["title"].label == "Title" and f["title"].required is True
    assert any("min(3)" in v for v in f["title"].validation)
    assert f["qty"].input_type == "number" and f["qty"].required
    assert "min=1" in f["qty"].validation and "max=9" in f["qty"].validation
    assert f["kind"].input_type == "select" and f["notes"].input_type == "textarea"
    assert screen.screen_name == "OrderForm"


def test_react_actions_navigation_and_composition(tmp_path: Path) -> None:
    files = {
        "app/items/page.tsx": """
import Link from 'next/link';
import { ItemList } from '../components/ItemList';
export default function ItemsPage() {
  const router = useRouter();
  useEffect(() => { fetch('/api/items'); }, []);
  async function removeItem(id: number) {
    await axios.delete(`/api/items/${id}`);
    router.push('/items');
  }
  return <div><ItemList /><Link href="/items/new">New</Link></div>;
}
""",
        "app/components/ItemList.tsx": "export function ItemList(){ return <ul/> }",
    }
    routes = [
        RouteSurface(
            name="/items",
            path="/items",
            source_refs=[SourceRef(file_path="app/items/page.tsx")],
        )
    ]
    screens = _run(tmp_path, files, routes=routes)
    page = next(s for s in screens if s.route_ref == "/items")
    refs = {(a.trigger, a.api_ref) for a in page.actions}
    assert ("load", "GET /api/items") in refs
    assert any(a.api_ref == "DELETE /api/items/:param" for a in page.actions)
    assert set(page.navigation_targets) == {"/items", "/items/new"}
    assert page.uses_components == ["ItemList"]
    # A component with no fields/actions/route is not a screen.
    assert all(s.screen_name != "ItemList" for s in screens)


def test_html_template_form(tmp_path: Path) -> None:
    html = """
<form method="post" action="/users/new">
  <label for="email">E-mail</label>
  <input id="email" name="email" type="email" required maxlength="80">
  <input name="age" type="number">
  <input type="submit" value="Go">
</form>
<a href="/users">All users</a>
"""
    (screen,) = _run(tmp_path, {"templates/new_user.html": html})
    f = {x.name: x for x in screen.fields}
    assert f["email"].label == "E-mail" and f["email"].required
    assert "maxlength=80" in f["email"].validation
    assert [a.api_ref for a in screen.actions] == ["POST /users/new"]
    assert screen.navigation_targets == ["/users"]
    assert screen.framework == "html-template"


def test_vue_sfc_vmodel_and_axios(tmp_path: Path) -> None:
    vue = """
<template>
  <form @submit.prevent="save">
    <input v-model="form.name" type="text" required>
    <input v-model="form.email" type="email">
  </form>
</template>
<script>
export default { methods: { save() { axios.post('/api/users', this.form) } } }
</script>
"""
    (screen,) = _run(tmp_path, {"src/UserForm.vue": vue})
    assert {f.name for f in screen.fields} == {"name", "email"}
    assert any(a.api_ref == "POST /api/users" for a in screen.actions)
    assert screen.framework == "vue"


def test_mapping_chains_field_to_api_and_model_with_gaps(tmp_path: Path) -> None:
    code = """
export function F() {
  async function onSubmit() { await fetch('/api/users', { method: 'POST' }); }
  return <form onSubmit={onSubmit}>
    <input name="name" /><input name="nickname" /><input name="email" />
  </form>;
}
"""
    screens = _run(tmp_path, {"F.tsx": code})
    api = ApiSurface(
        name="POST /api/users",
        method="POST",
        path="/api/users",
        request_schema={
            "fields": [
                {"name": "name", "type": "string", "required": True, "source": "body"},
                {
                    "name": "email",
                    "type": "string",
                    "required": False,
                    "source": "body",
                },
            ],
            "confidence": "inferred",
        },
    )
    model = ModelSurface(
        name="User",
        entity_name="User",
        fields=[
            ModelField(name="name", field_type="str"),
            ModelField(name="email", field_type="str"),
        ],
    )
    map_screen_fields(screens, [api], [model])
    by = {f.name: f for f in screens[0].fields}
    assert by["name"].bound_model_field == "User.name"
    assert by["name"].bound_api_field == "POST /api/users#name"
    assert by["email"].bound_model_field == "User.email"
    assert by["nickname"].bound_model_field is None
    assert "no matching API request field" in by["nickname"].gap


def test_no_form_files_yield_nothing(tmp_path: Path) -> None:
    assert _run(tmp_path, {"util.tsx": "export const x = 1;"}) == []


def test_wtforms_screens_link_routes_and_merge_form_contract(tmp_path: Path) -> None:
    """Flask-WTF forms (microblog eval): fields, validators, handler link, contract."""
    forms = """\
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    password2 = PasswordField("Repeat", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Register")

    def validate_username(self, username):
        pass
"""
    routes = """\
from flask import render_template
from forms import RegistrationForm


@bp.route("/register", methods=["POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        pass
    return render_template("register.html", form=form)
"""
    api = ApiSurface(
        name="POST /auth/register",
        method="POST",
        path="/auth/register",
        source_refs=[SourceRef(file_path="routes.py", start_line=5)],
        request_schema={"unknown": True},
    )
    model = ModelSurface(
        name="User",
        entity_name="User",
        fields=[
            ModelField(name="username", field_type="str"),
            ModelField(name="email", field_type="str"),
        ],
    )
    screens = _run(
        tmp_path, {"forms.py": forms, "routes.py": routes}, apis=[api], models=[model]
    )
    (screen,) = [s for s in screens if s.framework == "wtforms"]
    f = {x.name: x for x in screen.fields}
    assert set(f) == {"username", "email", "password", "password2"}  # submit skipped
    assert f["username"].validation == [
        "required",
        "minLength=3",
        "maxLength=20",
        "custom validation (validate_username)",
    ]
    assert (
        f["password2"].validation == ["required", "equal_to=password"]
        and f["password"].input_type == "password"
    )
    assert screen.route_ref == "/auth/register"
    assert [a.api_ref for a in screen.actions] == ["POST /auth/register"]
    assert (
        f["username"].bound_model_field == "User.username"
        and f["email"].bound_model_field == "User.email"
    )
    assert f["password"].bound_model_field is None  # honest gap, not a guess
    # the handler's unknown contract became the form's declared contract
    assert api.request_schema["confidence"] == "declared"
    assert {x["name"] for x in api.request_schema["fields"]} == {
        "username",
        "email",
        "password",
        "password2",
    }
    assert all(x["source"] == "form" for x in api.request_schema["fields"])

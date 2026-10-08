"""Contract failure cases; synthetic data lives only in temporary directories."""

import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import art_pipeline as art


SCHEMA = art.read_json(art.ROOT / art.SCHEMA_PATH)


class ArtContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source_root = self.root / "art/sources"
        self.source_root.mkdir(parents=True)
        # Not an actual image: geometric tests mock the independently checked PNG parser.
        (self.source_root / "texture.png").write_bytes(b"synthetic fixture, not a PNG")
        self.model = {
            "schema_version": 1, "id": "redstonefamily:test", "target": "native_entity",
            "texture": {"source": "texture.png", "width": 64, "height": 32},
            "parts": [{"name": "body", "parent": None, "pivot": [0, 0, 0], "rotation": [0, 0, 0],
                       "cubes": [{"name": "cube", "origin": [-4, 16, -4], "size": [8, 8, 8], "uv": [0, 0], "mirror": False}]}],
            "animation": {"type": "procedural", "profile": "vanilla_slime", "parameters": {}},
        }

    def write_json(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def validate_model(self):
        with patch.object(art, "png_size", return_value=(64, 32)):
            art.validate_model(self.model, SCHEMA, self.source_root)

    def asset(self):
        source = self.write_json("art/sources/source.json", {})
        output = self.write_json("src/main/resources/assets/redstonefamily/models/item/test.json", {})
        return {"id": "redstonefamily:test", "kind": "item_model", "source": "source.json",
                "source_sha256": art.hash_file(source), "inputs": [], "generator": "future-item-v1",
                "outputs": [{"path": output.relative_to(self.root).as_posix(), "sha256": art.hash_file(output)}]}

    def manifest(self, assets):
        self.write_json(art.MANIFEST_PATH, {"schema_version": 1, "assets": assets})

    def test_valid_geometry(self):
        self.validate_model()

    def test_schema_rejects_unknown_fields_and_missing_required(self):
        for mutate in (lambda data: data.update(meshes=[]), lambda data: data.pop("parts")):
            data = copy.deepcopy(self.model)
            mutate(data)
            with self.subTest(data=data), self.assertRaises(art.ValidationError):
                art.validate_schema(data, SCHEMA)

    def test_version_and_bool_as_integer(self):
        for value in (2, True):
            self.model["schema_version"] = value
            with self.subTest(value=value), self.assertRaises(art.ValidationError):
                self.validate_model()

    def test_schema_fails_on_unknown_validation_keywords(self):
        with self.assertRaisesRegex(art.ValidationError, "unsupported schema"):
            art.validate_schema({}, {"made_up_constraint": True})

    def test_zero_negative_and_fractional_sizes(self):
        for value in (0, -1, 0.5):
            self.model["parts"][0]["cubes"][0]["size"][0] = value
            with self.subTest(value=value), self.assertRaises(art.ValidationError):
                self.validate_model()

    def test_uv_bounds(self):
        self.model["parts"][0]["cubes"][0]["uv"] = [40, 30]
        with self.assertRaisesRegex(art.ValidationError, "UV outside"):
            self.validate_model()

    def test_duplicate_parts_and_cubes(self):
        self.model["parts"].append(copy.deepcopy(self.model["parts"][0]))
        with self.assertRaisesRegex(art.ValidationError, "duplicate part"):
            self.validate_model()
        self.model["parts"].pop()
        self.model["parts"][0]["cubes"] *= 2
        with self.assertRaisesRegex(art.ValidationError, "duplicate cube"):
            self.validate_model()

    def test_missing_parent(self):
        self.model["parts"][0]["parent"] = "missing"
        with self.assertRaisesRegex(art.ValidationError, "missing parent"):
            self.validate_model()

    def test_parent_cycle(self):
        self.model["parts"][0]["parent"] = "body"
        with self.assertRaisesRegex(art.ValidationError, "parent cycle"):
            self.validate_model()

    def test_missing_texture(self):
        self.model["texture"]["source"] = "absent.png"
        with self.assertRaisesRegex(art.ValidationError, "missing texture"):
            self.validate_model()

    def test_texture_dimensions(self):
        self.model["texture"]["width"] = 32
        with self.assertRaisesRegex(art.ValidationError, "dimensions"):
            self.validate_model()

    def test_path_traversal_and_absolute_paths(self):
        for value in ("../outside.png", "/outside.png", "C:/outside.png", "a\\b.png", "a//b.png", "./a.png"):
            with self.subTest(value=value), self.assertRaises(art.ValidationError):
                art.safe_path(self.source_root, value)

    def test_empty_manifest_is_explicit(self):
        self.manifest([])
        self.write_json(art.SCHEMA_PATH, SCHEMA)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(art.main(["validate", "--root", str(self.root)]), 0)
        self.assertIn("zero exported assets", output.getvalue())

    def test_manifest_duplicate_id(self):
        asset = self.asset()
        self.manifest([asset, asset])
        with self.assertRaisesRegex(art.ValidationError, "duplicate asset ID"):
            art.validate_manifest(self.root, SCHEMA)

    def test_two_generators_cannot_own_same_output(self):
        first = self.asset()
        second = copy.deepcopy(first)
        second.update(id="redstonefamily:other", generator="another-generator")
        self.manifest([first, second])
        with self.assertRaisesRegex(art.ValidationError, "duplicate output owner"):
            art.validate_manifest(self.root, SCHEMA)

    def test_main_and_generated_logical_collision(self):
        first = self.asset()
        second = copy.deepcopy(first)
        second["id"] = "redstonefamily:other"
        second["outputs"][0]["path"] = second["outputs"][0]["path"].replace("src/main", "src/generated")
        self.write_json(second["outputs"][0]["path"], {})
        self.manifest([first, second])
        with self.assertRaisesRegex(art.ValidationError, "duplicate output owner"):
            art.validate_manifest(self.root, SCHEMA)
        with self.assertRaisesRegex(art.ValidationError, "duplicate resource"):
            art.resource_check(self.root)

    def test_stale_source_and_modified_output(self):
        asset = self.asset()
        self.manifest([asset])
        self.assertEqual(art.validate_manifest(self.root, SCHEMA, fresh=True), 1)
        self.write_json("art/sources/source.json", {"changed": True})
        with self.assertRaisesRegex(art.ValidationError, "source changed"):
            art.validate_manifest(self.root, SCHEMA, fresh=True)
        self.write_json("art/sources/source.json", {})
        self.write_json(asset["outputs"][0]["path"], {"hand_edited": True})
        with self.assertRaisesRegex(art.ValidationError, "output changed"):
            art.validate_manifest(self.root, SCHEMA, fresh=True)

    def test_input_dependency_freshness(self):
        asset = self.asset()
        dependency = self.write_json("art/sources/dependency.json", {})
        asset["inputs"] = [{"path": "dependency.json", "sha256": art.hash_file(dependency)}]
        self.manifest([asset])
        dependency.write_text('{"changed":true}', encoding="utf-8")
        with self.assertRaisesRegex(art.ValidationError, "input dependency changed"):
            art.validate_manifest(self.root, SCHEMA, fresh=True)

    def test_missing_output(self):
        asset = self.asset()
        (self.root / asset["outputs"][0]["path"]).unlink()
        self.manifest([asset])
        with self.assertRaisesRegex(art.ValidationError, "missing exported output"):
            art.validate_manifest(self.root, SCHEMA)

    def test_output_outside_approved_roots(self):
        asset = self.asset()
        asset["outputs"][0]["path"] = "build.gradle"
        self.manifest([asset])
        with self.assertRaisesRegex(art.ValidationError, "outside allowed"):
            art.validate_manifest(self.root, SCHEMA)

    def test_old_data_directory_and_wrong_namespace(self):
        for relative in ("data/redstonefamily/recipes/test.json", "assets/examplemod/lang/en_us.json", "data/redstonefamily/tags/items/test.json"):
            with self.subTest(relative=relative):
                path = self.write_json("src/main/resources/" + relative, {})
                with self.assertRaises(art.ValidationError):
                    art.resource_check(self.root)
                path.unlink()

    def test_model_missing_texture_reference(self):
        self.write_json("src/main/resources/assets/redstonefamily/models/item/test.json",
                        {"parent": "minecraft:item/handheld", "textures": {"layer0": "redstonefamily:item/absent"}})
        with self.assertRaisesRegex(art.ValidationError, "missing model/texture"):
            art.resource_check(self.root)

    def test_model_parent_cycle(self):
        for name, parent in (("one", "two"), ("two", "one")):
            self.write_json(f"src/main/resources/assets/redstonefamily/models/item/{name}.json", {"parent": f"redstonefamily:item/{parent}"})
        with self.assertRaisesRegex(art.ValidationError, "model parent cycle"):
            art.resource_check(self.root)

    def test_json_duplicate_keys_and_nonfinite(self):
        path = self.root / "invalid.json"
        for data in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}'):
            path.write_text(data, encoding="utf-8")
            with self.subTest(data=data), self.assertRaises(art.ValidationError):
                value = art.read_json(path)
                art.validate_schema(value, {"type": "object", "additionalProperties": {"type": "number"}})

    def test_png_parser_rejects_non_image(self):
        with self.assertRaisesRegex(art.ValidationError, "PNG signature"):
            art.png_size(self.source_root / "texture.png")

    def test_export_is_unavailable_and_read_only(self):
        before = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(art.main(["export", "--root", str(self.root)]), 1)
        self.assertIn("not implemented", errors.getvalue())
        after = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        self.assertEqual(before, after)

    def test_check_does_not_change_tracked_input_bytes(self):
        self.manifest([self.asset()])
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        art.validate_manifest(self.root, SCHEMA, fresh=True)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})


if __name__ == "__main__":
    unittest.main()

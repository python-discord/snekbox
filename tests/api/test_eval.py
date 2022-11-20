from tests.api import SnekAPITestCase


class TestEvalResource(SnekAPITestCase):
    PATH = "/eval"

    def test_post_valid_200(self):
        body = {"args": ["-c", "print('output')"]}
        result = self.simulate_post(self.PATH, json=body)

        self.assertEqual(result.status_code, 200)
        self.assertEqual("output", result.json["stdout"])
        self.assertEqual(0, result.json["returncode"])

    def test_post_invalid_schema_400(self):
        body = {"stuff": "foo"}
        result = self.simulate_post(self.PATH, json=body)

        self.assertEqual(result.status_code, 400)

        expected = {
            "title": "Request data failed validation",
            "description": "'args' is a required property",
        }

        self.assertEqual(expected, result.json)

    def test_post_invalid_data_400(self):
        bodies = ({"args": 400}, {"args": [], "files": [215]})
        expects = ["400 is not of type 'array'", "215 is not of type 'object'"]
        for body, expected in zip(bodies, expects):
            with self.subTest():
                result = self.simulate_post(self.PATH, json=body)

                self.assertEqual(result.status_code, 400)

                expected_json = {
                    "title": "Request data failed validation",
                    "description": expected,
                }
                self.assertEqual(expected_json, result.json)

    def test_post_invalid_content_type_415(self):
        body = "{'input': 'foo'}"
        headers = {"Content-Type": "application/xml"}
        result = self.simulate_post(self.PATH, body=body, headers=headers)

        self.assertEqual(result.status_code, 415)

        expected = {
            "title": "415 Unsupported Media Type",
            "description": "application/xml is an unsupported media type.",
        }

        self.assertEqual(expected, result.json)

    def test_disallowed_method_405(self):
        result = self.simulate_get(self.PATH)
        self.assertEqual(result.status_code, 405)

    def test_options_allow_post_only(self):
        result = self.simulate_options(self.PATH)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers.get("Allow"), "POST")

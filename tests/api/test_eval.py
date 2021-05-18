from tests.api import SnekAPITestCase


class TestEvalResource(SnekAPITestCase):
    PATH = "/eval"

    def test_post_valid_200(self):
        body = {"input": "foo"}
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
            "description": "'input' is a required property"
        }

        self.assertEqual(expected, result.json)

    def test_post_invalid_data_400(self):
        input_body = {"input": 400}
        args_body = {"input": "", "args": [400]}

        input_result = self.simulate_post(self.PATH, json=input_body)
        args_result = self.simulate_post(self.PATH, json=args_body)

        self.assertEqual(input_result.status_code, 400)
        self.assertEqual(args_result.status_code, 400)

        expected = {
            "title": "Request data failed validation",
            "description": "400 is not of type 'string'"
        }

        self.assertEqual(expected, input_result.json)
        self.assertEqual(expected, args_result.json)

    def test_post_invalid_content_type_415(self):
        body = "{'input': 'foo'}"
        headers = {"Content-Type": "application/xml"}
        result = self.simulate_post(self.PATH, body=body, headers=headers)

        self.assertEqual(result.status_code, 415)

        expected = {
            "title": "Unsupported media type",
            "description": "application/xml is an unsupported media type."
        }

        self.assertEqual(expected, result.json)

    def test_disallowed_method_405(self):
        result = self.simulate_get(self.PATH)
        self.assertEqual(result.status_code, 405)

    def test_options_allow_post_only(self):
        result = self.simulate_options(self.PATH)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers.get("Allow"), "POST")

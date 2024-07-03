from datetime import datetime

from ninja.renderers import BaseRenderer

import orjson


class Renderer(BaseRenderer):

    media_type = "application/json"
    format = "json"
    charset = ""

    def render(self, data, **options):
        return orjson.dumps(
            {
                "data": data,
                "message_code": "SUCCESS",
                "message": "Success",
                "error_code": 0,
                "current_time": datetime.now(),
            }
        )

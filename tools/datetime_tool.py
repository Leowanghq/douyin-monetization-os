"""
Date/time tool — get current date, time, or day of week.
"""

from datetime import datetime

from agent.tools import BaseTool


class DateTimeTool(BaseTool):
    name = "get_datetime"
    description = "Get the current date and time. Use this when asked about today's date, current time, or day of week."
    parameters = {
        "format": {
            "type": "string",
            "description": "What to return: 'full' for date+time, 'date' for date only, 'time' for time only, 'weekday' for day of week. Default: 'full'.",
        },
    }

    def execute(self, format: str = "full") -> str:
        now = datetime.now()
        if format == "date":
            return now.strftime("%Y-%m-%d")
        elif format == "time":
            return now.strftime("%H:%M:%S")
        elif format == "weekday":
            days_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            days_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            return f"{now.strftime('%Y-%m-%d')} is {days_en[now.weekday()]} ({days_cn[now.weekday()]})"
        else:
            return now.strftime("%Y-%m-%d %H:%M:%S %A")

"""Single-table storage: DynamoDB in AWS, a JSON file locally. Plans are stored as a JSON string
attribute so floats need no Decimal conversion.

Keys: pk=SCHOOL#<id>  sk=PROFILE | PLAN#<date> | AUDIT#<iso time>"""

import json
import os
import threading
from datetime import datetime, timezone

from . import config


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class StateConflict(Exception):
    pass


class _Local:
    _lock = threading.Lock()

    def __init__(self):
        os.makedirs(config.LOCAL_DATA_DIR, exist_ok=True)
        self.path = os.path.join(config.LOCAL_DATA_DIR, "store.json")

    def _load(self) -> dict:
        if not os.path.exists(self.path):
            return {}
        with open(self.path) as f:
            return json.load(f)

    def get(self, pk, sk):
        with self._lock:
            return self._load().get(f"{pk}|{sk}")

    def put(self, item):
        with self._lock:
            data = self._load()
            data[f"{item['pk']}|{item['sk']}"] = item
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(data, f, ensure_ascii=False)

    def query(self, pk, prefix, limit=50, newest_first=True):
        with self._lock:
            items = [v for v in self._load().values() if v["pk"] == pk and v["sk"].startswith(prefix)]
        items.sort(key=lambda i: i["sk"], reverse=newest_first)
        return items[:limit]

    def scan_prefix(self, sk):
        with self._lock:
            return [v for v in self._load().values() if v["sk"] == sk]

    def transition(self, pk, sk, expected, attrs):
        with self._lock:
            data = self._load()
            item = data.get(f"{pk}|{sk}")
            if not item or item.get("status") not in expected:
                raise StateConflict(item.get("status") if item else "missing")
            item.update(attrs)
            with open(self.path, "w") as f:
                json.dump(data, f, ensure_ascii=False)
            return item


class _Dynamo:
    def __init__(self):
        import boto3
        self.table = boto3.resource("dynamodb").Table(config.TABLE_NAME)

    def get(self, pk, sk):
        return self.table.get_item(Key={"pk": pk, "sk": sk}).get("Item")

    def put(self, item):
        self.table.put_item(Item=item)

    def query(self, pk, prefix, limit=50, newest_first=True):
        from boto3.dynamodb.conditions import Key
        resp = self.table.query(KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(prefix),
                                ScanIndexForward=not newest_first, Limit=limit)
        return resp["Items"]

    def scan_prefix(self, sk):
        from boto3.dynamodb.conditions import Attr
        return self.table.scan(FilterExpression=Attr("sk").eq(sk))["Items"]

    def transition(self, pk, sk, expected, attrs):
        """Conditional update: only succeeds if the current status is one of `expected`."""
        from botocore.exceptions import ClientError
        names = {"#s": "status", **{f"#a{i}": k for i, k in enumerate(attrs)}}
        values = {**{f":e{i}": v for i, v in enumerate(expected)},
                  **{f":v{i}": v for i, v in enumerate(attrs.values())}}
        try:
            return self.table.update_item(
                Key={"pk": pk, "sk": sk},
                UpdateExpression="SET " + ", ".join(f"#a{i} = :v{i}" for i in range(len(attrs))),
                ConditionExpression=f"#s IN ({', '.join(f':e{i}' for i in range(len(expected)))})",
                ExpressionAttributeNames=names, ExpressionAttributeValues=values,
                ReturnValues="ALL_NEW")["Attributes"]
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise StateConflict("status changed") from e
            raise


_backend = None


def backend():
    global _backend
    if _backend is None:
        _backend = _Dynamo() if config.running_in_aws() else _Local()
    return _backend


def get_school(sid):
    item = backend().get(f"SCHOOL#{sid}", "PROFILE")
    return json.loads(item["data"]) if item else None


def put_school(school):
    backend().put({"pk": f"SCHOOL#{school['id']}", "sk": "PROFILE",
                   "data": json.dumps(school, ensure_ascii=False), "updated_at": now()})


def list_schools():
    return [json.loads(i["data"]) for i in backend().scan_prefix("PROFILE")]


def get_plan_item(sid, date):
    item = backend().get(f"SCHOOL#{sid}", f"PLAN#{date}")
    if item and item.get("data"):
        item = {**item, "plan": json.loads(item["data"])}
    return item


def put_plan_item(sid, date, plan=None, **attrs):
    item = backend().get(f"SCHOOL#{sid}", f"PLAN#{date}") or {"pk": f"SCHOOL#{sid}", "sk": f"PLAN#{date}"}
    if plan is not None:
        item["data"] = json.dumps(plan, ensure_ascii=False)
    item.update({k: v for k, v in attrs.items()})
    item["updated_at"] = now()
    backend().put(item)
    return item


def transition_plan(sid, date, expected, **attrs):
    """Atomically move a plan between states; raises StateConflict if someone else got there first."""
    return backend().transition(f"SCHOOL#{sid}", f"PLAN#{date}", tuple(expected), {**attrs, "updated_at": now()})


def list_plan_items(sid, limit=20):
    return backend().query(f"SCHOOL#{sid}", "PLAN#", limit=limit)


def audit(sid, event, detail=""):
    backend().put({"pk": f"SCHOOL#{sid}", "sk": f"AUDIT#{now()}", "event": event, "detail": detail})


def list_audit(sid, limit=30):
    return [{"at": i["sk"][6:], "event": i["event"], "detail": i.get("detail", "")}
            for i in backend().query(f"SCHOOL#{sid}", "AUDIT#", limit=limit)]

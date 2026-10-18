#!/usr/bin/env python3
"""Check HDFS readiness without launching another JVM."""
import json
import sys
import urllib.request


def check_readiness(payload):
    beans = payload.get("beans", [])
    if not beans:
        raise ValueError("NameNode JMX is not ready")
    info = beans[0]
    # Missing fields must fail closed, not appear to be a writable filesystem.
    if info["Safemode"] != "":
        raise ValueError("NameNode is still in safe mode")
    if not json.loads(info["LiveNodes"]):
        raise ValueError("NameNode has no live DataNode")


def main():
    url = "http://127.0.0.1:9870/jmx?qry=Hadoop:service=NameNode,name=NameNodeInfo"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            check_readiness(json.load(response))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"HDFS not ready: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

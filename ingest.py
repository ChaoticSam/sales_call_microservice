import pandas as pd
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import SessionLocal
from app.models import Call

CSV_FILE = "dataset/sample.csv"


def parse_datetime(ts):
    """Convert Twitter time format to Python datetime"""
    return datetime.strptime(ts, "%a %b %d %H:%M:%S %z %Y")


def normalize_conversations(df):
    """Group tweets into conversations based on reply chains"""
    tweet_map = {row["tweet_id"]: row for _, row in df.iterrows()}
    conversations = []

    visited = set()

    for _, row in df.iterrows():
        tid = row["tweet_id"]
        if tid in visited:
            continue

        # Start from an agent tweet that replies to customer
        if not row["is_customer"] and pd.notnull(row["in_reply_to"]):
            convo = []
            current = row
            while True:
                convo.append(current)
                visited.add(current["tweet_id"])

                reply_id = current["in_reply_to"]
                if pd.isna(reply_id) or reply_id not in tweet_map:
                    break

                current = tweet_map[reply_id]

            conversations.append(list(reversed(convo)))  # Earliest first

    return conversations


def build_call(convo):
    """Build a Call object from a conversation list"""
    agent = next((row for row in convo if not row["is_customer"]), None)
    customer = next((row for row in convo if row["is_customer"]), None)

    if not agent or not customer:
        return None

    start_time = parse_datetime(convo[0]["timestamp"])
    end_time = parse_datetime(convo[-1]["timestamp"])
    duration = int((end_time - start_time).total_seconds())

    transcript = "\n".join([
        f'{row["author_id"]}: {row["text"]}' for row in convo
    ])

    return {
        "call_id": str(agent["tweet_id"]),  # use agent's first reply
        "agent_id": agent["author_id"],
        "customer_id": customer["author_id"],
        "language": "en",
        "start_time": start_time,
        "duration_seconds": duration,
        "transcript": transcript
    }


async def insert_calls(call_data):
    async with SessionLocal() as session:
        async with session.begin():
            for call_dict in call_data:
                if call_dict:
                    call = Call(**call_dict)
                    session.add(call)


async def main():
    df = pd.read_csv(CSV_FILE, names=[
        "tweet_id", "author_id", "is_customer", "timestamp",
        "text", "in_reply_to", "status_id"
    ])
    print(f"[INFO] Loaded {len(df)} tweets")

    conversations = normalize_conversations(df)
    print(f"[INFO] Found {len(conversations)} conversations")

    call_data = [build_call(convo) for convo in conversations]
    call_data = [c for c in call_data if c]  # remove None

    await insert_calls(call_data)
    print("[INFO] Ingestion complete")


if __name__ == "__main__":
    asyncio.run(main())

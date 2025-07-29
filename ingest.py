import pandas as pd
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import Call

# Path to your dataset
CSV_FILE = "dataset/sample.csv"

def parse_datetime(ts: str) -> datetime:
    """Convert Twitter-style timestamp to Python datetime."""
    return datetime.strptime(ts, "%a %b %d %H:%M:%S %z %Y")

def normalize_conversations(df: pd.DataFrame):
    """
    Group tweets into conversations based on the in_response_to_tweet_id chain.
    We start from any agent tweet (inbound=False) that replies to someone.
    """
    # Map tweet_id -> row
    tweet_map = {row["tweet_id"]: row for _, row in df.iterrows()}
    conversations = []
    visited = set()

    for _, row in df.iterrows():
        tid = row["tweet_id"]
        if tid in visited:
            continue

        # Only start threads at agent replies
        if not row["inbound"] and pd.notnull(row["in_response_to_tweet_id"]):
            convo = []
            current = row

            # Traverse backward through the in_response_to chain
            while True:
                convo.append(current)
                visited.add(current["tweet_id"])

                parent_id = current["in_response_to_tweet_id"]
                # stop if no parent or missing in map
                if pd.isna(parent_id) or parent_id not in tweet_map:
                    break

                current = tweet_map[parent_id]

            # We collected in reverse (agent → customer → ...), so reverse to chronological
            conversations.append(list(reversed(convo)))

    return conversations

def build_call(convo: list):
    # Identify agent vs. customer
    agent_msg    = next((m for m in convo if not m["inbound"]), None)
    customer_msg = next((m for m in convo if     m["inbound"]), None)
    if agent_msg is None or customer_msg is None:
        return None

    # Times
    start = parse_datetime(convo[0]["created_at"])
    end   = parse_datetime(convo[-1]["created_at"])
    duration = int((end - start).total_seconds())

    # Stitch transcript
    transcript = "\n".join([
        f'{ "Agent" if not m["inbound"] else "Customer" } '
        f'({m["author_id"]}): {m["text"]}'
        for m in convo
    ])

    return {
        "call_id":           str(agent_msg["tweet_id"]),
        "agent_id":          agent_msg["author_id"],
        "customer_id":       customer_msg["author_id"],
        "language":          "en",
        "start_time":        start,
        "duration_seconds":  duration,
        "transcript":        transcript
    }

async def insert_calls(call_dicts: list[dict]):
    """Bulk insert call records into Postgres using AsyncSession."""
    async with SessionLocal() as session: 
        async with session.begin():
            for cd in call_dicts:
                if cd:
                    session.add(Call(**cd))

async def main():
    # Load CSV with correct column names
    df = pd.read_csv(
        CSV_FILE,
        names=[
            "tweet_id",
            "author_id",
            "inbound",
            "created_at",
            "text",
            "response_tweet_id",
            "in_response_to_tweet_id"
        ],
        dtype={"tweet_id": str, "author_id": str, "inbound": bool},
        header=0  # skip existing header row
    )
    print(f"[INFO] Loaded {len(df)} tweets")

    # Normalize conversations
    conversations = normalize_conversations(df)
    print(f"[INFO] Found {len(conversations)} conversations")

    # Build call dicts
    call_data = [build_call(c) for c in conversations]
    call_data = [c for c in call_data if c]  # drop None

    print(f"[INFO] Inserting {len(call_data)} calls into DB")
    await insert_calls(call_data)
    print("[INFO] Ingestion complete")

if __name__ == "__main__":
    asyncio.run(main())

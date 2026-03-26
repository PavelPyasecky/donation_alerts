import datetime
import json

from redis.asyncio import Redis

from models.donations import Donater
from models.top_donaters import DonationEvent
from top_donaters.utils import _decode, _ensure_datetime, _parse_datetime, _to_decimal


class TopDonatersCache:
    def __init__(self, redis: Redis):
        self.redis = redis

    def _prefix(self, author_id: int, period: str) -> str:
        return f"top_donaters:{author_id}:{period}"

    def _keys(self, author_id: int, period: str) -> dict[str, str]:
        base = self._prefix(author_id, period)
        return {
            "rank": f"{base}:rank",
            "total": f"{base}:total",
            "count": f"{base}:count",
            "last": f"{base}:last",
            "time": f"{base}:time",
            "don": f"{base}:don",
        }

    async def seed_from_list(self, author_id: int, period: str, donaters: list[Donater]) -> None:
        keys = self._keys(author_id, period)
        if await self.redis.zcard(keys["rank"]) > 0:
            return

        pipe = self.redis.pipeline()
        for donater in donaters:
            amount = _to_decimal(donater.total_amount)
            amount_float = float(amount)
            pipe.zadd(keys["rank"], {donater.donor_name: amount_float})
            pipe.hset(keys["total"], donater.donor_name, str(amount))
            pipe.hset(keys["count"], donater.donor_name, int(donater.total_count))
            if donater.last_created_at:
                pipe.hset(keys["last"], donater.donor_name, donater.last_created_at.isoformat())
        await pipe.execute()

    async def record_donation(
        self,
        author_id: int,
        period: str,
        donation: DonationEvent,
        window_seconds: int | None,
    ) -> None:
        keys = self._keys(author_id, period)
        created_at = _ensure_datetime(donation.timestamp)
        timestamp = created_at.timestamp()

        if window_seconds is not None:
            await self.evict_old(author_id, period, timestamp - window_seconds)

        amount_float = float(donation.amount)
        donation_payload = json.dumps(
            {"donor": donation.donor_name, "amount": str(donation.amount)}, ensure_ascii=True
        )

        pipe = self.redis.pipeline()
        pipe.zadd(keys["time"], {donation.donation_id: timestamp})
        pipe.hset(keys["don"], donation.donation_id, donation_payload)
        pipe.hincrbyfloat(keys["total"], donation.donor_name, amount_float)
        pipe.hincrby(keys["count"], donation.donor_name, 1)
        pipe.zincrby(keys["rank"], amount_float, donation.donor_name)
        await pipe.execute()

        await self._update_last_seen(keys["last"], donation.donor_name, created_at)

    async def evict_old(self, author_id: int, period: str, cutoff_ts: float) -> None:
        keys = self._keys(author_id, period)
        batch_size = 500

        while True:
            old_ids = await self.redis.zrangebyscore(keys["time"], 0, cutoff_ts, start=0, num=batch_size)
            if not old_ids:
                break

            values = await self.redis.hmget(keys["don"], old_ids)
            updates: list[tuple[str, float]] = []
            for raw in values:
                if not raw:
                    continue
                payload = json.loads(raw)
                donor = payload.get("donor")
                amount = _to_decimal(payload.get("amount"))
                if donor:
                    updates.append((donor, float(amount)))

            if updates:
                pipe = self.redis.pipeline()
                for donor, amount in updates:
                    pipe.hincrbyfloat(keys["total"], donor, -amount)
                    pipe.hincrby(keys["count"], donor, -1)
                    pipe.zincrby(keys["rank"], -amount, donor)
                results = await pipe.execute()
                count_results = results[1::3]

                cleanup_pipe = self.redis.pipeline()
                for (donor, _), count in zip(updates, count_results):
                    if count is None or int(count) <= 0:
                        cleanup_pipe.hdel(keys["total"], donor)
                        cleanup_pipe.hdel(keys["count"], donor)
                        cleanup_pipe.hdel(keys["last"], donor)
                        cleanup_pipe.zrem(keys["rank"], donor)
                await cleanup_pipe.execute()

            pipe = self.redis.pipeline()
            pipe.hdel(keys["don"], *old_ids)
            pipe.zrem(keys["time"], *old_ids)
            await pipe.execute()

    async def get_top(self, author_id: int, period: str, limit: int) -> list[Donater]:
        keys = self._keys(author_id, period)
        donors = await self.redis.zrevrange(keys["rank"], 0, limit - 1, withscores=True)
        if not donors:
            return []

        donor_names = [_decode(name) for name, _ in donors]
        totals = await self.redis.hmget(keys["total"], donor_names)
        counts = await self.redis.hmget(keys["count"], donor_names)
        last_times = await self.redis.hmget(keys["last"], donor_names)

        result: list[Donater] = []
        for donor_name, total, count, last in zip(donor_names, totals, counts, last_times):
            total = _decode(total)
            count = _decode(count)
            last = _decode(last)
            if total is None or count is None:
                continue
            last_dt = _parse_datetime(last)
            result.append(
                Donater(
                    donor_name=donor_name,
                    total_amount=str(total),
                    total_count=int(count),
                    last_created_at=last_dt or datetime.datetime.fromtimestamp(0, datetime.timezone.utc),
                )
            )
        return result

    async def _update_last_seen(self, last_key: str, donor_name: str, created_at: datetime.datetime) -> None:
        existing = await self.redis.hget(last_key, donor_name)
        created_iso = created_at.isoformat()
        if not existing:
            await self.redis.hset(last_key, donor_name, created_iso)
            return
        existing_dt = _parse_datetime(existing)
        if existing_dt is None or created_at > existing_dt:
            await self.redis.hset(last_key, donor_name, created_iso)

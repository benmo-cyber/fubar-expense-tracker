import re
from sqlalchemy.orm import Session
from app.models import Merchant, MerchantAlias

SUFFIXES = {
    "airlines", "airline", "airways", "inc", "llc", "co", "company",
    "corp", "corporation", "store", "stores", "the",
}


def normalize_merchant(name: str) -> str:
    words = re.findall(r"[a-z0-9]+", (name or "").lower())
    kept = [word for word in words if word not in SUFFIXES]
    return " ".join(kept or words)


def resolve_merchant(db: Session, name: str) -> Merchant | None:
    cleaned = " ".join((name or "").split())
    if not cleaned:
        return None
    key = normalize_merchant(cleaned)
    alias = db.query(MerchantAlias).filter(MerchantAlias.alias == key).first()
    if alias:
        return alias.merchant
    for merchant in db.query(Merchant).all():
        existing = normalize_merchant(merchant.name)
        if not existing or not key:
            continue
        shorter, longer = sorted((existing, key), key=len)
        if len(shorter) >= 6 and (longer == shorter or longer.startswith(shorter + " ")):
            db.add(MerchantAlias(merchant_id=merchant.id, alias=key))
            return merchant
    merchant = Merchant(name=cleaned)
    db.add(merchant)
    db.flush()
    db.add(MerchantAlias(merchant_id=merchant.id, alias=key))
    return merchant

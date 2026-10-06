from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ValidationRequest(BaseModel):
    dataset_path: Optional[str] = None


class ProcessRequest(BaseModel):
    dataset_path: Optional[str] = None
    sample_rows: int = 200000


class BudgetRequest(BaseModel):
    total_budget: float = 0.0
    target_price: Optional[float] = None
    preferred_category: Optional[str] = None
    minimum_price: Optional[float] = None
    maximum_price: Optional[float] = None


class ShoppingPlanItem(BaseModel):
    product_id: str
    quantity: int = 1
    observed_price: float = 0.0


class ShoppingPlanRequest(BaseModel):
    product_id: str
    quantity: int = 1
    observed_price: float = 0.0

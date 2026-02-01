from fastapi import FastAPI, Query
from LMS import fetch_combined_product_info

app = FastAPI()

@app.get("/lms")
def lms(product_id: int = Query(..., description="productId / groupNumber")):
    return fetch_combined_product_info(product_id)

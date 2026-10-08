import math


def calculate_pagination(
    page: int,
    page_size: int,
    total: int,
):
    total_pages = math.ceil(total / page_size) if total else 0

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


def get_offset(
    page: int,
    page_size: int,
):
    return (page - 1) * page_size
from dataclasses import dataclass


@dataclass
class PaginationParams:
    skip: int = 0
    limit: int = 100

    @property
    def page(self) -> int:
        if self.limit == 0:
            return 1
        return (self.skip // self.limit) + 1


def paginate(total: int, page: int, page_size: int, data: list) -> dict:
    return {
        "success": True,
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": data,
    }

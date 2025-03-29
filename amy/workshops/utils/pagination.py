from itertools import chain
from typing import Iterable, TypeVar

from django.core.paginator import EmptyPage, Page, PageNotAnInteger
from django.core.paginator import Paginator as DjangoPaginator
from django.db.models import Model, QuerySet
from django.http import HttpRequest

_T = TypeVar("_T")
_MT = TypeVar("_MT", bound=Model)  # Model type

ITEMS_PER_PAGE = 25


class Paginator(DjangoPaginator[_T]):
    """Everything should work as in django.core.paginator.Paginator, except
    this class provides additional generator for nicer set of pages."""

    _page_number = None

    def page(self, number: int | str) -> Page[_T]:
        """Overridden to store retrieved page number somewhere."""
        self._page_number = number
        return super().page(number)

    def paginate_sections(self) -> Iterable[int | None]:
        """Divide pagination range into 3 sections.

        Each section should contain approx. 5 links.  If sections are
        overlapping, they're merged.
        The results might be:
        * L…M…R
        * LM…R
        * L…MR
        * LMR
        where L - left section, M - middle section, R - right section, and "…"
        stands for a separator.
        """
        index = int(self._page_number) or 1 if self._page_number else 1
        items = self.page_range
        length = self.num_pages

        L = items[0:5]

        four_after_index = index + 4
        one_after_index = index + 1
        if index - 3 == 5:
            # Fix when two sets, L_s and M_s, are disjoint but make a sequence
            # [... 3 4, 5 6 ...], then there should not be dots between them
            four_before_index = index - 4
            M = items[four_before_index:four_after_index] or items[0:one_after_index]
        else:
            three_before_index = index - 3
            M = items[three_before_index:four_after_index] or items[0:one_after_index]

        if index + 4 == length - 5:
            # Fix when two sets, M_s and R_s, are disjoint but make a sequence
            # [... 3 4, 5 6 ...], then there should not be dots between them
            R = items[-6:]
        else:
            R = items[-5:]

        L_s = set(L)
        M_s = set(M)
        R_s = set(R)

        dots = [None]

        D1 = L_s.isdisjoint(M_s)
        D2 = M_s.isdisjoint(R_s)
        D3 = L_s.isdisjoint(R_s)

        pagination: Iterable[int | None]

        if D1 and D2 and D3:
            # L…M…R
            pagination = chain(L, dots, M, dots, R)
        elif not D1 and D2 and D3:
            # LM…R
            pagination = chain(sorted(L_s | M_s), dots, R)
        elif D1 and not D2 and D3:
            # L…MR
            pagination = chain(L, dots, sorted(M_s | R_s))
        elif not D3:
            # tough situation, we may have split something wrong,
            # so lets just display all pages
            pagination = items
        else:
            # LMR
            pagination = iter(sorted(L_s | M_s | R_s))

        return pagination


def get_pagination_items(request: HttpRequest, all_objects: QuerySet[_MT]) -> Page[_MT]:
    """Select paginated items."""

    # Get parameters.
    items = request.GET.get("items_per_page", ITEMS_PER_PAGE)
    if items != "all":
        try:
            items = int(items)
        except ValueError:
            items = ITEMS_PER_PAGE
    else:
        # Show everything.
        items = all_objects.count()

    # Figure out where we are.
    page = request.GET.get("page", 1)

    # Show selected items.
    paginator = Paginator(all_objects, items)

    # Select the pages.
    try:
        result = paginator.page(page)

    # If page is not an integer, deliver first page.
    except PageNotAnInteger:
        result = paginator.page(1)

    # If page is out of range, deliver last page of results.
    except EmptyPage:
        result = paginator.page(paginator.num_pages)

    return result

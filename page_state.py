"""Pages are saved in the layout; legacy buttons remain as an active-page view."""
from copy import deepcopy
import uuid


def empty_buttons():
    return [[{'color': [0, 0, 0], 'text': ''} for _ in range(9)] for _ in range(9)]


def validate_buttons(buttons):
    if not isinstance(buttons, list) or len(buttons) != 9:
        raise ValueError('A page must contain a 9 by 9 pad grid.')
    for column in buttons:
        if not isinstance(column, list) or len(column) != 9:
            raise ValueError('A page must contain a 9 by 9 pad grid.')
        for button in column:
            if not isinstance(button, dict) or not isinstance(button.get('text'), str):
                raise ValueError('Each pad needs script text.')
            colour = button.get('color')
            if not isinstance(colour, list) or len(colour) != 3 or any(type(value) is not int or not 0 <= value <= 255 for value in colour):
                raise ValueError('Each pad needs three RGB values between 0 and 255.')


class PageBook:
    def __init__(self):
        self.reset()

    def reset(self):
        self.pages = [{'id': 'main', 'name': 'Page 1', 'buttons': empty_buttons()}]
        self.active = 0
        self.generation = getattr(self, 'generation', 0) + 1

    @property
    def current(self):
        return self.pages[self.active]

    def capture(self, texts, colours):
        self.current['buttons'] = [[{'text': texts[x][y], 'color': deepcopy(colours[x][y])}
                                    for y in range(9)] for x in range(9)]

    def add(self, name=None):
        if len(self.pages) >= 128:
            raise ValueError('A layout supports up to 128 pages.')
        name = (name or f'Page {len(self.pages) + 1}').strip()
        if not name or any(page['name'].casefold() == name.casefold() for page in self.pages):
            raise ValueError('Choose a unique page name.')
        self.pages.append({'id': uuid.uuid4().hex, 'name': name, 'buttons': empty_buttons()})
        return len(self.pages) - 1

    def rename(self, name):
        name = name.strip()
        if not name or any(page is not self.current and page['name'].casefold() == name.casefold() for page in self.pages):
            raise ValueError('Choose a unique page name.')
        self.current['name'] = name

    def remove(self):
        if len(self.pages) == 1:
            raise ValueError('Keep at least one page.')
        removed = self.pages.pop(self.active)
        self.active = min(self.active, len(self.pages) - 1)
        self.generation += 1
        return removed['id']

    def resolve(self, target):
        if isinstance(target, int):
            if not 0 <= target < len(self.pages):
                raise ValueError('Page number is out of range.')
            return target
        for index, page in enumerate(self.pages):
            if str(target).casefold() in (page['name'].casefold(), page['id'].casefold()):
                return index
        if str(target).isdigit():
            return self.resolve(int(target) - 1)
        raise ValueError('No page named ' + str(target))

    def activate(self, target):
        self.active = self.resolve(target)
        self.generation += 1

    def to_layout(self, version='0.2.0'):
        return {'version': version, 'buttons': deepcopy(self.current['buttons']),
                'pages': deepcopy(self.pages), 'active_page_id': self.current['id']}

    def load(self, layout):
        pages = deepcopy(layout.get('pages') or [{'id': 'main', 'name': 'Page 1', 'buttons': layout['buttons']}])
        if not isinstance(pages, list) or not pages or len(pages) > 128:
            raise ValueError('A layout must contain between 1 and 128 pages.')
        ids, names = set(), set()
        for page in pages:
            if not isinstance(page, dict) or not isinstance(page.get('id'), str) or not page['id'] or not isinstance(page.get('name'), str) or not page['name'].strip():
                raise ValueError('Each page needs an ID and name.')
            if page['id'] in ids or page['name'].casefold() in names:
                raise ValueError('Page IDs and names must be unique.')
            ids.add(page['id'])
            names.add(page['name'].casefold())
            validate_buttons(page['buttons'])
        active = next((i for i, page in enumerate(pages) if page['id'] == layout.get('active_page_id')), 0)
        self.pages, self.active = pages, active
        self.generation += 1


book = PageBook()

# GraphQL Query Templates for Monday.com API v2 (Version 2024-01+)

GET_BOARDS_LIST = """
query {
  boards (limit: 50) {
    id
    name
    description
  }
}
"""

GET_BOARD_COLUMNS = """
query ($board_id: ID!) {
  boards (ids: [$board_id]) {
    id
    name
    columns {
      id
      title
      type
    }
  }
}
"""

GET_BOARD_ITEMS = """
query ($board_id: ID!, $cursor: String) {
  boards (ids: [$board_id]) {
    id
    name
    items_page (limit: 100, cursor: $cursor) {
      cursor
      items {
        id
        name
        column_values {
          id
          text
          value
        }
      }
    }
  }
}
"""

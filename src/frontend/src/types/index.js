/**
 * File types dùng chung của Frontend (Shared Types & Constants)
 * Lưu ý: File dùng chung cho toàn bộ ứng dụng.
 */

/**
 * @typedef {Object} Category
 * @property {number} id
 * @property {string} name
 * @property {string|null} [description]
 */

/**
 * @typedef {Object} Book
 * @property {number} id
 * @property {string} title
 * @property {string} author
 * @property {string} isbn
 * @property {string|null} [publisher]
 * @property {number|null} [published_year]
 * @property {number} category_id
 * @property {string} category_name
 * @property {number} total_copies
 * @property {number} available_copies
 * @property {boolean} is_deleted
 */

/**
 * @typedef {Object} BookListResponse
 * @property {Book[]} items
 * @property {number} total
 * @property {number} page
 * @property {number} page_size
 * @property {number} total_pages
 */

/**
 * @typedef {Object} BorrowRecord
 * @property {number} id
 * @property {number} book_id
 * @property {string} book_title
 * @property {number} member_id
 * @property {string} member_name
 * @property {string} member_code
 * @property {string} borrow_date
 * @property {string} due_date
 * @property {string|null} return_date
 * @property {string} status
 * @property {string|null} notes
 */

export const PAGE_SIZE_DEFAULT = 5;

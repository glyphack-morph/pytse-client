TEST_PATH=./tests

.PHONY: unit_test offline_test e2e_test install build audit

unit_test:
	uv run python -m unittest

# The tests that do not call the TSETMC servers (run by CI on every
# supported Python version, see .github/workflows/python_versions.yml).
SCRAPER_TESTS=tests.test_scraper.test_symbol_scraper
offline_test:
	uv run python -m unittest \
		tests.test_symbols_data \
		$(SCRAPER_TESTS).TestSymbolScraper.test_market_symbols_from_market_watch \
		$(SCRAPER_TESTS).TestSymbolScraper.test_match_search_results \
		$(SCRAPER_TESTS).TestSymbolScraper.test_deduplicate_keeps_first \
		$(SCRAPER_TESTS).TestSymbolScraper.test_remove_active_indexes_from_old \
		$(SCRAPER_TESTS).TestSymbolScraper.test_failed_search_keeps_old_indexes \
		$(SCRAPER_TESTS).TestIndicesScraper.test_parse_index_title \
		$(SCRAPER_TESTS).TestIndicesScraper.test_build_indices

e2e_test:
	uv run python $(TEST_PATH)/test_download/download_all.py
	uv run python $(TEST_PATH)/test_ticker/ticker_e2e.py

install:
	uv sync

build:
	uv build

audit:
	uv audit --preview-features audit-command

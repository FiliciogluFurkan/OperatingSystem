# GTU-C312 CPU Simulator and Operating System Project Makefile
# CSE 312/504 Operating Systems
# Author: [Student Name]

# Variables
PYTHON = python3
SIMULATOR = gtu_cpu_sim.py
OS_PROGRAM = os_program_fixed.txt
OUTPUT_DIR = outputs
REPORT_DIR = reports

# Default target
.DEFAULT_GOAL := help

# Help target
.PHONY: help
help:
	@echo "GTU-C312 CPU Simulator Makefile"
	@echo "================================"
	@echo ""
	@echo "Available targets:"
	@echo "  run           - Run simulation with debug level 0"
	@echo "  debug1        - Run with debug level 1 (instruction trace)"
	@echo "  debug2        - Run with debug level 2 (step-by-step)"
	@echo "  debug3        - Run with debug level 3 (thread table)"
	@echo "  test-all      - Run all debug levels and save outputs"
	@echo "  clean         - Clean output files"
	@echo "  setup         - Create necessary directories"
	@echo "  validate      - Validate input files exist"
	@echo "  report        - Generate execution report"
	@echo "  help          - Show this help message"

# Setup directories
.PHONY: setup
setup:
	@echo "Setting up project directories..."
	@mkdir -p $(OUTPUT_DIR)
	@mkdir -p $(REPORT_DIR)
	@echo "Directories created successfully."

# Validate required files
.PHONY: validate
validate:
	@echo "Validating project files..."
	@if [ ! -f $(SIMULATOR) ]; then \
		echo "ERROR: $(SIMULATOR) not found!"; \
		exit 1; \
	fi
	@if [ ! -f $(OS_PROGRAM) ]; then \
		echo "ERROR: $(OS_PROGRAM) not found!"; \
		exit 1; \
	fi
	@echo "All required files present."

# Run simulation with debug level 0 (production mode)
.PHONY: run
run: validate setup
	@echo "Running GTU-C312 simulation (Debug Level 0)..."
	$(PYTHON) $(SIMULATOR) $(OS_PROGRAM) -D 0 | tee $(OUTPUT_DIR)/simulation_debug0.txt
	@echo "Simulation completed. Output saved to $(OUTPUT_DIR)/simulation_debug0.txt"

# Run with debug level 1 (instruction trace)
.PHONY: debug1
debug1: validate setup
	@echo "Running GTU-C312 simulation (Debug Level 1 - Instruction Trace)..."
	$(PYTHON) $(SIMULATOR) $(OS_PROGRAM) -D 1 > $(OUTPUT_DIR)/simulation_debug1.txt 2>&1
	@echo "Debug Level 1 completed. Output saved to $(OUTPUT_DIR)/simulation_debug1.txt"

# Run with debug level 2 (step-by-step with keyboard input)
.PHONY: debug2
debug2: validate setup
	@echo "Running GTU-C312 simulation (Debug Level 2 - Step by Step)..."
	@echo "NOTE: This mode requires keyboard input after each instruction."
	@echo "Press Enter to continue each step, Ctrl+C to abort."
	$(PYTHON) $(SIMULATOR) $(OS_PROGRAM) -D 2 | tee $(OUTPUT_DIR)/simulation_debug2.txt

# Run with debug level 3 (thread table debugging)
.PHONY: debug3
debug3: validate setup
	@echo "Running GTU-C312 simulation (Debug Level 3 - Thread Table Debug)..."
	$(PYTHON) $(SIMULATOR) $(OS_PROGRAM) -D 3 > $(OUTPUT_DIR)/simulation_debug3.txt 2>&1
	@echo "Debug Level 3 completed. Output saved to $(OUTPUT_DIR)/simulation_debug3.txt"

# Test all debug levels
.PHONY: test-all
test-all: validate setup
	@echo "Running all debug levels..."
	@echo "1/4: Debug Level 0 (Production)"
	@$(MAKE) run --no-print-directory
	@echo ""
	@echo "2/4: Debug Level 1 (Instruction Trace)"
	@$(MAKE) debug1 --no-print-directory
	@echo ""
	@echo "3/4: Debug Level 3 (Thread Table)"
	@$(MAKE) debug3 --no-print-directory
	@echo ""
	@echo "4/4: Generating summary report..."
	@$(MAKE) report --no-print-directory
	@echo ""
	@echo "All tests completed! Check $(OUTPUT_DIR)/ for results."

# Generate execution report
.PHONY: report
report: setup
	@echo "Generating execution report..."
	@echo "GTU-C312 Simulation Report" > $(REPORT_DIR)/execution_report.txt
	@echo "=========================" >> $(REPORT_DIR)/execution_report.txt
	@echo "Generated on: $$(date)" >> $(REPORT_DIR)/execution_report.txt
	@echo "" >> $(REPORT_DIR)/execution_report.txt
	@echo "Files Generated:" >> $(REPORT_DIR)/execution_report.txt
	@echo "===============" >> $(REPORT_DIR)/execution_report.txt
	@ls -la $(OUTPUT_DIR)/ >> $(REPORT_DIR)/execution_report.txt 2>/dev/null || echo "No output files found." >> $(REPORT_DIR)/execution_report.txt
	@echo "" >> $(REPORT_DIR)/execution_report.txt
	@if [ -f $(OUTPUT_DIR)/simulation_debug0.txt ]; then \
		echo "Debug Level 0 Summary:" >> $(REPORT_DIR)/execution_report.txt; \
		echo "=====================" >> $(REPORT_DIR)/execution_report.txt; \
		tail -20 $(OUTPUT_DIR)/simulation_debug0.txt >> $(REPORT_DIR)/execution_report.txt; \
		echo "" >> $(REPORT_DIR)/execution_report.txt; \
	fi
	@echo "Report generated: $(REPORT_DIR)/execution_report.txt"

# Performance test
.PHONY: performance
performance: validate setup
	@echo "Running performance test..."
	@echo "Performance Test Results" > $(OUTPUT_DIR)/performance_test.txt
	@echo "=======================" >> $(OUTPUT_DIR)/performance_test.txt
	@echo "Test Date: $$(date)" >> $(OUTPUT_DIR)/performance_test.txt
	@echo "" >> $(OUTPUT_DIR)/performance_test.txt
	@echo "Running 5 iterations to measure consistency..." >> $(OUTPUT_DIR)/performance_test.txt
	@for i in 1 2 3 4 5; do \
		echo "Iteration $$i:" >> $(OUTPUT_DIR)/performance_test.txt; \
		time $(PYTHON) $(SIMULATOR) $(OS_PROGRAM) -D 0 2>&1 | grep "Total cycles" >> $(OUTPUT_DIR)/performance_test.txt; \
		echo "" >> $(OUTPUT_DIR)/performance_test.txt; \
	done
	@echo "Performance test completed. Results saved to $(OUTPUT_DIR)/performance_test.txt"

# Memory usage analysis
.PHONY: memory-analysis
memory-analysis: validate setup
	@echo "Running memory usage analysis..."
	@echo "Memory Usage Analysis" > $(OUTPUT_DIR)/memory_analysis.txt
	@echo "====================" >> $(OUTPUT_DIR)/memory_analysis.txt
	@echo "Analysis Date: $$(date)" >> $(OUTPUT_DIR)/memory_analysis.txt
	@echo "" >> $(OUTPUT_DIR)/memory_analysis.txt
	@if command -v valgrind >/dev/null 2>&1; then \
		echo "Running with Valgrind..." >> $(OUTPUT_DIR)/memory_analysis.txt; \
		valgrind --tool=massif --massif-out-file=$(OUTPUT_DIR)/massif.out $(PYTHON) $(SIMULATOR) $(OS_PROGRAM) -D 0 >> $(OUTPUT_DIR)/memory_analysis.txt 2>&1; \
	else \
		echo "Valgrind not available. Running basic memory analysis..." >> $(OUTPUT_DIR)/memory_analysis.txt; \
		/usr/bin/time -v $(PYTHON) $(SIMULATOR) $(OS_PROGRAM) -D 0 >> $(OUTPUT_DIR)/memory_analysis.txt 2>&1; \
	fi
	@echo "Memory analysis completed. Results saved to $(OUTPUT_DIR)/memory_analysis.txt"

# Quick test for development
.PHONY: quick
quick: validate
	@echo "Quick test run..."
	$(PYTHON) $(SIMULATOR) $(OS_PROGRAM) -D 0

# Check code syntax
.PHONY: syntax-check
syntax-check:
	@echo "Checking Python syntax..."
	@$(PYTHON) -m py_compile $(SIMULATOR)
	@echo "Syntax check passed."

# Lint the code
.PHONY: lint
lint:
	@echo "Running code linting..."
	@if command -v pylint >/dev/null 2>&1; then \
		pylint $(SIMULATOR) || echo "Pylint warnings found (non-fatal)"; \
	else \
		echo "Pylint not available. Install with: pip3 install pylint"; \
	fi

# Create project archive
.PHONY: archive
archive: clean
	@echo "Creating project archive..."
	@tar -czf gtu_c312_project_$$(date +%Y%m%d_%H%M%S).tar.gz \
		$(SIMULATOR) \
		$(OS_PROGRAM) \
		Makefile \
		README.md \
		$(OUTPUT_DIR)/ \
		$(REPORT_DIR)/ \
		2>/dev/null || tar -czf gtu_c312_project_$$(date +%Y%m%d_%H%M%S).tar.gz \
		$(SIMULATOR) \
		$(OS_PROGRAM) \
		Makefile
	@echo "Archive created: gtu_c312_project_$$(date +%Y%m%d_%H%M%S).tar.gz"

# Clean output files
.PHONY: clean
clean:
	@echo "Cleaning output files..."
	@rm -rf $(OUTPUT_DIR)/*.txt
	@rm -rf $(REPORT_DIR)/*.txt
	@rm -f *.pyc
	@rm -f __pycache__/*
	@rmdir __pycache__ 2>/dev/null || true
	@echo "Clean completed."

# Deep clean (remove directories too)
.PHONY: deep-clean
deep-clean: clean
	@echo "Deep cleaning..."
	@rm -rf $(OUTPUT_DIR)
	@rm -rf $(REPORT_DIR)
	@rm -f *.tar.gz
	@echo "Deep clean completed."

# Show project status
.PHONY: status
status:
	@echo "GTU-C312 Project Status"
	@echo "======================"
	@echo "Python Version: $$($(PYTHON) --version)"
	@echo "Simulator File: $(SIMULATOR) $$(if [ -f $(SIMULATOR) ]; then echo '[EXISTS]'; else echo '[MISSING]'; fi)"
	@echo "OS Program File: $(OS_PROGRAM) $$(if [ -f $(OS_PROGRAM) ]; then echo '[EXISTS]'; else echo '[MISSING]'; fi)"
	@echo "Output Directory: $(OUTPUT_DIR) $$(if [ -d $(OUTPUT_DIR) ]; then echo '[EXISTS]'; else echo '[MISSING]'; fi)"
	@echo "Report Directory: $(REPORT_DIR) $$(if [ -d $(REPORT_DIR) ]; then echo '[EXISTS]'; else echo '[MISSING]'; fi)"
	@echo ""
	@echo "Recent Output Files:"
	@ls -la $(OUTPUT_DIR)/ 2>/dev/null || echo "No output files found."

# Install dependencies (if needed)
.PHONY: install-deps
install-deps:
	@echo "Installing Python dependencies..."
	@echo "No additional dependencies required for this project."
	@echo "Ensure Python 3.x is installed."

# Run comprehensive test suite
.PHONY: test-suite
test-suite: syntax-check validate test-all performance report
	@echo ""
	@echo "==================================="
	@echo "GTU-C312 Test Suite Completed!"
	@echo "==================================="
	@echo "Check the following files:"
	@echo "- $(OUTPUT_DIR)/simulation_debug*.txt for execution logs"
	@echo "- $(OUTPUT_DIR)/performance_test.txt for performance data"
	@echo "- $(REPORT_DIR)/execution_report.txt for summary"

# Development mode (quick iterations)
.PHONY: dev
dev:
	@echo "Development mode - Quick test and feedback"
	@$(MAKE) syntax-check --no-print-directory
	@$(MAKE) quick --no-print-directory

# Show file sizes
.PHONY: size-report
size-report:
	@echo "Project File Sizes"
	@echo "=================="
	@ls -lh $(SIMULATOR) $(OS_PROGRAM) 2>/dev/null || echo "Some files missing"
	@if [ -d $(OUTPUT_DIR) ]; then \
		echo ""; \
		echo "Output Files:"; \
		ls -lh $(OUTPUT_DIR)/ 2>/dev/null || echo "No output files"; \
	fi
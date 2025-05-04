#!/usr/bin/env python3
"""
Issue Creator Script for Crypto Trading Bot Code Analysis

This script parses code analysis reports and creates tickets in GitHub Issues
for critical findings that need to be addressed, with special focus on
cryptocurrency trading specific concerns.
"""

import os
import json
import re
import argparse
import requests
from datetime import datetime
from collections import defaultdict

# Configure your GitHub repository settings
GITHUB_API_URL = "https://api.github.com"
GITHUB_REPO = os.environ.get("GITHUB_REPO", "your-username/Long_Term_crypto_trading_bot")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # Set this as an environment variable

# Report directories
CODE_ANALYSIS_DIR = "code_analysis_reports"
REPORTS_DIR = "reports"

# Issue creation thresholds
SECURITY_SEVERITY_THRESHOLD = "high"  # Create issues for high and critical security findings
CODE_QUALITY_THRESHOLD = 10  # Number of issues in a file to trigger an issue


def parse_security_reports():
    """Parse security reports and extract critical vulnerabilities."""
    issues = []
    
    # Parse Python security report from safety
    try:
        with open(f"{CODE_ANALYSIS_DIR}/python_security_report.txt", "r") as f:
            content = f.read()
            if "No known security vulnerabilities found" not in content:
                # Extract vulnerability details
                vulnerabilities = []
                current_vuln = None
                
                for line in content.split('\n'):
                    if line.startswith('=> '):  # New vulnerability
                        if current_vuln:
                            vulnerabilities.append(current_vuln)
                        current_vuln = {'package': line.split('=> ')[1].split(' ')[0]}
                    elif current_vuln and 'Vulnerability ID:' in line:
                        current_vuln['id'] = line.split('Vulnerability ID: ')[1].strip()
                    elif current_vuln and 'Affected:' in line:
                        current_vuln['affected'] = line.split('Affected: ')[1].strip()
                    elif current_vuln and 'Remediation:' in line:
                        current_vuln['remediation'] = line.split('Remediation: ')[1].strip()
                    elif current_vuln and not line.startswith('   '):  # Description lines
                        current_vuln['description'] = line.strip() if 'description' not in current_vuln else current_vuln['description'] + " " + line.strip()
                
                if current_vuln:
                    vulnerabilities.append(current_vuln)
                
                # Create GitHub issue for each critical vulnerability or group if many
                if len(vulnerabilities) > 5:
                    # Group vulnerabilities if there are many
                    issues.append({
                        "title": f"Security: {len(vulnerabilities)} vulnerable dependencies found",
                        "body": (
                            f"**Multiple security vulnerabilities found in dependencies**\n\n"
                            f"A total of {len(vulnerabilities)} vulnerabilities were found in project dependencies.\n\n"
                            f"Top vulnerabilities:\n" + 
                            "\n".join([f"- {v.get('package')}: {v.get('description', 'No description')} ({v.get('remediation', 'No remediation info')})" 
                                    for v in vulnerabilities[:5]]) +
                            "\n\nSee the full report for details on all vulnerabilities."
                        ),
                        "labels": ["security", "critical", "dependencies"]
                    })
                else:
                    # Create individual issues for each vulnerability if there are few
                    for vuln in vulnerabilities:
                        issues.append({
                            "title": f"Security: {vuln.get('package')} vulnerability",
                            "body": (
                                f"**Security vulnerability found**\n\n"
                                f"Package: {vuln.get('package')}\n"
                                f"Vulnerability ID: {vuln.get('id', 'Unknown')}\n"
                                f"Affected versions: {vuln.get('affected', 'Unknown')}\n"
                                f"Remediation: {vuln.get('remediation', 'Unknown')}\n\n"
                                f"Description: {vuln.get('description', 'No description available')}"
                            ),
                            "labels": ["security", "critical", "dependencies"]
                        })
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"No Python security report found or report is invalid: {e}")
    
    # Parse custom crypto security issues
    try:
        with open(f"{CODE_ANALYSIS_DIR}/crypto_security_issues.txt", "r") as f:
            content = f.read()
            if "Issues:" in content:
                issue_section = content.split("Issues:")[1].strip()
                crypto_issues = [line.strip()[2:] for line in issue_section.split("\n") if line.strip().startswith("- ")]
                
                if crypto_issues:
                    issues.append({
                        "title": "Crypto-specific security issues detected",
                        "body": (
                            "**Cryptocurrency-specific security issues found**\n\n"
                            "The following security issues specific to cryptocurrency applications were detected:\n\n" + 
                            "\n".join([f"- {issue}" for issue in crypto_issues]) +
                            "\n\n### Impact\n\n"
                            "These issues could potentially lead to:\n"
                            "- Exposure of API keys or private credentials\n"
                            "- Insecure API communications\n"
                            "- Unauthorized access to exchange accounts\n"
                            "- Potential financial loss\n\n"
                            "### Recommended Action\n\n"
                            "Please review these issues and implement secure credential handling practices:\n"
                            "- Store all API keys in environment variables or a secure vault\n"
                            "- Always use HTTPS for API communications\n"
                            "- Implement proper encryption for any sensitive data"
                        ),
                        "labels": ["security", "critical", "crypto-specific"]
                    })
    except FileNotFoundError:
        print("No crypto security issues report found")
    
    return issues


def parse_exchange_consistency_reports():
    """Parse exchange API consistency reports."""
    issues = []
    
    try:
        with open(f"{CODE_ANALYSIS_DIR}/exchange_api_consistency.txt", "r") as f:
            content = f.read()
            if "Issues:" in content:
                # Extract the issues
                issue_section = content.split("Issues:")[1].strip()
                exchange_issues = [line.strip()[2:] for line in issue_section.split("\n") if line.strip().startswith("- ")]
                
                if exchange_issues:
                    issues.append({
                        "title": "Exchange API inconsistencies detected",
                        "body": (
                            "**Exchange API Implementations are Inconsistent**\n\n"
                            "The following inconsistencies were found in exchange implementations:\n\n" +
                            "\n".join([f"- {issue}" for issue in exchange_issues]) +
                            "\n\n### Impact\n\n"
                            "Inconsistent exchange API implementations can cause:\n"
                            "- Runtime errors when trying to use unimplemented methods\n"
                            "- Unpredictable behavior when switching between exchanges\n"
                            "- Difficulties with the multi-exchange aggregator\n"
                            "- Potential trading failures in production\n\n"
                            "### Recommended Action\n\n"
                            "Implement the missing methods in each exchange class to ensure API consistency across all exchanges."
                        ),
                        "labels": ["bug", "exchange-api", "critical"]
                    })
    except FileNotFoundError:
        print("No exchange consistency report found")
    
    return issues


def parse_strategy_pattern_reports():
    """Parse strategy pattern verification reports."""
    issues = []
    
    try:
        with open(f"{CODE_ANALYSIS_DIR}/strategy_pattern_verification.txt", "r") as f:
            content = f.read()
            if "Issues:" in content:
                # Extract the issues
                issue_section = content.split("Issues:")[1].strip()
                strategy_issues = [line.strip()[2:] for line in issue_section.split("\n") if line.strip().startswith("- ")]
                
                if strategy_issues:
                    issues.append({
                        "title": "Trading strategy implementation issues",
                        "body": (
                            "**Trading Strategy Pattern Violations Detected**\n\n"
                            "The following issues were found in strategy implementations:\n\n" +
                            "\n".join([f"- {issue}" for issue in strategy_issues]) +
                            "\n\n### Impact\n\n"
                            "Incomplete strategy implementations can lead to:\n"
                            "- Runtime errors when strategies are executed\n"
                            "- Null pointer exceptions\n"
                            "- Missing signals in the trading system\n"
                            "- Potential financial losses due to strategy failures\n\n"
                            "### Recommended Action\n\n"
                            "Each strategy class must implement all required methods from the base class. "
                            "Please implement the missing methods in each identified strategy."
                        ),
                        "labels": ["bug", "trading-strategy", "critical"]
                    })
    except FileNotFoundError:
        print("No strategy pattern report found")
    
    return issues


def parse_risk_management_reports():
    """Parse risk management validation reports."""
    issues = []
    
    try:
        with open(f"{CODE_ANALYSIS_DIR}/portfolio_risk_analysis.txt", "r") as f:
            content = f.read()
            if "Issues:" in content:
                # Extract the issues
                issue_section = content.split("Issues:")[1].strip()
                risk_issues = [line.strip()[2:] for line in issue_section.split("\n") if line.strip().startswith("- ")]
                
                # Group issues by strategy
                strategies_without_stoploss = []
                strategies_without_position_sizing = []
                
                for issue in risk_issues:
                    if "No stop-loss mechanism" in issue:
                        strategies_without_stoploss.append(issue.split(":")[0])
                    elif "No position sizing" in issue:
                        strategies_without_position_sizing.append(issue.split(":")[0])
                
                if risk_issues:
                    issues.append({
                        "title": "⚠️ Missing risk management controls in trading strategies",
                        "body": (
                            "**Critical Risk Management Issues Detected**\n\n"
                            "The following risk management issues were found:\n\n" +
                            "\n".join([f"- {issue}" for issue in risk_issues]) +
                            "\n\n### Impact\n\n"
                            "Trading without proper risk management can lead to:\n"
                            "- Catastrophic financial losses\n"
                            "- Account blow-ups during market volatility\n"
                            "- Unpredictable behavior in edge cases\n"
                            "- Inability to control maximum drawdown\n\n"
                            f"**Strategies missing stop-loss:** {', '.join(strategies_without_stoploss) if strategies_without_stoploss else 'None'}\n\n"
                            f"**Strategies missing position sizing:** {', '.join(strategies_without_position_sizing) if strategies_without_position_sizing else 'None'}\n\n"
                            "### Recommended Action\n\n"
                            "1. Implement stop-loss mechanisms in all strategies\n"
                            "2. Add position sizing based on risk percentage\n"
                            "3. Consider adding trailing stops for trend-following strategies\n"
                            "4. Add maximum drawdown protection at the portfolio level"
                        ),
                        "labels": ["bug", "risk-management", "critical", "high-priority"]
                    })
    except FileNotFoundError:
        print("No risk management report found")
    
    return issues


def parse_code_quality_reports():
    """Parse code quality reports and extract significant issues."""
    issues = []
    
    # Parse flake8 report
    try:
        with open(f"{CODE_ANALYSIS_DIR}/flake8_report.txt", "r") as f:
            lines = f.readlines()
            
            # Group issues by file
            file_issues = defaultdict(list)
            for line in lines:
                if ":" in line:
                    file_path = line.split(":")[0]
                    file_issues[file_path].append(line.strip())
            
            # Create issues for files with many problems
            for file_path, file_problems in file_issues.items():
                if len(file_problems) > CODE_QUALITY_THRESHOLD:
                    issues.append({
                        "title": f"Code quality: Improve {os.path.basename(file_path)}",
                        "body": (
                            f"**Code quality issues found in {file_path}**\n\n"
                            f"This file has {len(file_problems)} style issues reported by flake8.\n\n"
                            f"Example issues:\n" + 
                            "\n".join([f"- {p}" for p in file_problems[:5]]) +
                            f"\n\n(Plus {len(file_problems) - 5} more issues not shown here)"
                        ),
                        "labels": ["code-quality", "refactoring"]
                    })
    except FileNotFoundError:
        print("No flake8 report found")
    
    # Parse pylint report
    try:
        with open(f"{CODE_ANALYSIS_DIR}/pylint_report.txt", "r") as f:
            content = f.read()
            
            # Group issues by file
            file_pattern = re.compile(r'^(.+?):')
            file_issues = defaultdict(list)
            
            for line in content.split("\n"):
                match = file_pattern.match(line)
                if match:
                    file_path = match.group(1)
                    file_issues[file_path].append(line.strip())
            
            # Create issues for files with many problems
            for file_path, file_problems in file_issues.items():
                if len(file_problems) > CODE_QUALITY_THRESHOLD:
                    issues.append({
                        "title": f"Code quality: Refactor {os.path.basename(file_path)}",
                        "body": (
                            f"**Code quality issues found in {file_path}**\n\n"
                            f"This file has {len(file_problems)} issues reported by pylint.\n\n"
                            f"Example issues:\n" + 
                            "\n".join([f"- {p}" for p in file_problems[:5]]) +
                            f"\n\n(Plus {len(file_problems) - 5} more issues not shown here)"
                        ),
                        "labels": ["code-quality", "refactoring"]
                    })
    except FileNotFoundError:
        print("No pylint report found")
    
    return issues


def parse_test_coverage_report():
    """Parse test coverage report and create issues for low coverage."""
    issues = []
    
    try:
        with open(f"{CODE_ANALYSIS_DIR}/test_coverage.txt", "r") as f:
            content = f.read()
            coverage_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', content)
            
            if coverage_match:
                coverage = int(coverage_match.group(1))
                
                if coverage < 50:
                    issues.append({
                        "title": "Low test coverage detected",
                        "body": (
                            f"**Test coverage is critically low: {coverage}%**\n\n"
                            "Low test coverage can lead to:\n"
                            "- Undetected bugs in production\n"
                            "- Regression issues when making changes\n"
                            "- Difficulty maintaining and extending the codebase\n"
                            "- Higher risk when deploying new features\n\n"
                            "### Recommended Action\n\n"
                            "1. Add unit tests for core exchange functionality\n"
                            "2. Add unit tests for trading strategies\n"
                            "3. Add integration tests for the critical path of the trading system\n"
                            "4. Focus on testing error handling and edge cases"
                        ),
                        "labels": ["test", "technical-debt", "high-priority"]
                    })
                    
                    # Find modules with particularly low coverage
                    module_pattern = re.compile(r'(src/[\w/]+\.py)\s+\d+\s+\d+\s+(\d+)%')
                    matches = module_pattern.finditer(content)
                    
                    low_coverage_modules = []
                    for match in matches:
                        module_path = match.group(1)
                        module_coverage = int(match.group(2))
                        
                        if module_coverage < 20 and 'exchanges/' in module_path or 'strategies/' in module_path:
                            low_coverage_modules.append((module_path, module_coverage))
                    
                    if low_coverage_modules:
                        issues.append({
                            "title": "Critical modules have insufficient test coverage",
                            "body": (
                                "**Critical trading components lack adequate test coverage**\n\n"
                                "The following critical modules have very low test coverage:\n\n" +
                                "\n".join([f"- {module}: {coverage}% coverage" for module, coverage in low_coverage_modules]) +
                                "\n\n### Impact\n\n"
                                "Low test coverage in exchange adapters and trading strategies represents a significant risk:\n"
                                "- Exchange adapters may fail when connecting to real exchanges\n"
                                "- Trading strategies may have undetected logical errors\n"
                                "- Money could be lost due to untested edge cases\n\n"
                                "### Recommended Action\n\n"
                                "1. Add comprehensive unit tests for all exchange adapters\n"
                                "2. Write tests that validate strategy behavior with different market conditions\n"
                                "3. Add tests that verify proper error handling for API failures"
                            ),
                            "labels": ["test", "critical", "high-priority"]
                        })
    except FileNotFoundError:
        print("No test coverage report found")
        
    return issues


def parse_unused_code_reports():
    """Parse reports about unused code and extract issues."""
    issues = []
    
    # Parse unused Python code report
    try:
        with open(f"{CODE_ANALYSIS_DIR}/unused_python_code.txt", "r") as f:
            content = f.read()
            
            # Group by file
            file_pattern = re.compile(r'^(.+\.py):')
            current_file = None
            file_unused = defaultdict(list)
            
            for line in content.split("\n"):
                file_match = file_pattern.match(line)
                if file_match:
                    current_file = file_match.group(1)
                elif line.strip() and current_file:
                    file_unused[current_file].append(line.strip())
            
            # Create issues for files with multiple unused elements
            for file_path, unused_elements in file_unused.items():
                if len(unused_elements) > 3:  # Arbitrary threshold
                    issues.append({
                        "title": f"Unused code detected in {os.path.basename(file_path)}",
                        "body": (
                            f"**Unused code found in {file_path}**\n\n"
                            f"This file has {len(unused_elements)} potentially unused elements.\n\n"
                            f"Elements to review:\n" + 
                            "\n".join([f"- {element}" for element in unused_elements]) +
                            "\n\nConsider removing these unused elements to improve code maintainability."
                        ),
                        "labels": ["unused-code", "cleanup"]
                    })
    except FileNotFoundError:
        print("No unused Python code report found")
    
    return issues


def create_github_issue(issue_data):
    """Create an issue in GitHub."""
    if not GITHUB_TOKEN:
        print("WARNING: GITHUB_TOKEN not set, cannot create issues")
        return None
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.post(
            f"{GITHUB_API_URL}/repos/{GITHUB_REPO}/issues",
            headers=headers,
            json=issue_data
        )
        
        if response.status_code == 201:
            issue = response.json()
            print(f"Created issue #{issue['number']}: {issue['title']}")
            return issue
        else:
            print(f"Failed to create issue: {response.status_code} {response.text}")
            return None
    except Exception as e:
        print(f"Error creating GitHub issue: {e}")
        return None


def main():
    """Main function to parse reports and create issues."""
    parser = argparse.ArgumentParser(description="Create issues from code analysis reports")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually create issues, just print them")
    args = parser.parse_args()
    
    # Ensure report directories exist
    os.makedirs(CODE_ANALYSIS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # Collect issues from all reports
    all_issues = []
    
    # Collect security issues first (highest priority)
    security_issues = parse_security_reports()
    all_issues.extend(security_issues)
    
    # Collect crypto-specific issues (high priority)
    exchange_issues = parse_exchange_consistency_reports()
    all_issues.extend(exchange_issues)
    
    strategy_issues = parse_strategy_pattern_reports()
    all_issues.extend(strategy_issues)
    
    risk_management_issues = parse_risk_management_reports()
    all_issues.extend(risk_management_issues)
    
    # Medium priority issues
    test_coverage_issues = parse_test_coverage_report()
    all_issues.extend(test_coverage_issues)
    
    # Lower priority issues
    code_quality_issues = parse_code_quality_reports()
    all_issues.extend(code_quality_issues)
    
    unused_code_issues = parse_unused_code_reports()
    all_issues.extend(unused_code_issues)
    
    print(f"Found {len(all_issues)} issues to create")
    
    # Deduplicate issues by title
    unique_issues = {}
    for issue in all_issues:
        if issue['title'] not in unique_issues:
            unique_issues[issue['title']] = issue
    
    print(f"After deduplication: {len(unique_issues)} unique issues")
    
    # Create issues in GitHub (or just print them for dry run)
    for title, issue_data in unique_issues.items():
        # Add a timestamp and issue source to the body
        issue_data['body'] += f"\n\n---\n*Issue generated automatically by code analysis on {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
        
        if args.dry_run:
            print(f"Would create issue: {issue_data['title']}")
            print(f"  Labels: {', '.join(issue_data['labels'])}")
            print(f"  Body: {issue_data['body'][:100]}...\n")
        else:
            create_github_issue(issue_data)


if __name__ == "__main__":
    main()

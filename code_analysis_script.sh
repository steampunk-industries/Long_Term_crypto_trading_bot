#!/bin/bash
# Comprehensive Code Analysis Script for Crypto Trading Bot
# This script performs multiple types of analysis specific to cryptocurrency
# trading applications and generates a consolidated report

# Exit on error
set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting comprehensive code analysis for crypto trading bot...${NC}"

# Create a directory for reports
REPORT_DIR="./code_analysis_reports"
mkdir -p $REPORT_DIR

# Detect the application's tech stack
echo -e "\n${YELLOW}Detecting tech stack...${NC}"
PYTHON_FILES=$(find . -name "*.py" | wc -l)
JS_FILES=$(find . -name "*.js" | wc -l)
HTML_FILES=$(find . -name "*.html" | wc -l)

echo "Found $PYTHON_FILES Python files"
echo "Found $JS_FILES JavaScript files"
echo "Found $HTML_FILES HTML files"

# =====================
# 1. SECURITY SCANNING
# =====================
echo -e "\n${YELLOW}Running security scans...${NC}"

# Check Python dependencies for vulnerabilities
if [ $PYTHON_FILES -gt 0 ] && [ -f "requirements.txt" ]; then
  echo "Scanning Python dependencies for vulnerabilities..."
  pip install safety > /dev/null 2>&1 || true
  safety check -r requirements.txt --output text > $REPORT_DIR/python_security_report.txt || true
fi

# Check JavaScript dependencies for vulnerabilities
if [ $JS_FILES -gt 0 ] && [ -f "package.json" ]; then
  echo "Scanning JavaScript dependencies for vulnerabilities..."
  npm audit --json > $REPORT_DIR/js_security_report.json || true
fi

# Check for crypto-specific security issues
echo "Checking for crypto-specific security issues..."
python - << EOF > $REPORT_DIR/crypto_security_issues.txt
import glob
import re

issues = []

# Look for hardcoded API keys
py_files = glob.glob('./**/*.py', recursive=True)
for file in py_files:
  with open(file, 'r') as f:
    try:
      content = f.read()
      
      # Look for potential API keys
      api_key_patterns = [
        r'api_key\s*=\s*["\'][a-zA-Z0-9]{16,}["\']',
        r'apikey\s*=\s*["\'][a-zA-Z0-9]{16,}["\']',
        r'secret\s*=\s*["\'][a-zA-Z0-9]{16,}["\']',
        r'password\s*=\s*["\'][^"\']+["\']'
      ]
      
      for pattern in api_key_patterns:
        matches = re.findall(pattern, content)
        if matches:
          issues.append(f"{file}: Possible hardcoded credentials detected")
          break
          
      # Check for unsafe HTTP without TLS
      if re.search(r'http://api\.[a-zA-Z0-9-]+\.(com|io|org)', content) and not file.endswith('test_'):
        issues.append(f"{file}: Using insecure HTTP for API communication")
        
    except UnicodeDecodeError:
      # Skip binary files
      pass

if issues:
  print("Crypto Security Issues:")
  for issue in issues:
    print(f"- {issue}")
else:
  print("No obvious crypto security issues found.")
EOF

# =====================
# 2. CODE QUALITY CHECKS
# =====================
echo -e "\n${YELLOW}Running code quality checks...${NC}"

# Python code quality (flake8 for style, pylint for deeper analysis)
if [ $PYTHON_FILES -gt 0 ]; then
  echo "Analyzing Python code quality..."
  pip install flake8 pylint > /dev/null 2>&1 || true
  flake8 --max-line-length=100 --statistics --count . > $REPORT_DIR/flake8_report.txt || true
  pylint --output-format=text $(find . -name "*.py") > $REPORT_DIR/pylint_report.txt || true
fi

# JavaScript code quality (ESLint)
if [ $JS_FILES -gt 0 ]; then
  echo "Analyzing JavaScript code quality..."
  if [ -f ".eslintrc.js" ] || [ -f ".eslintrc.json" ] || [ -f ".eslintrc.yml" ]; then
    npx eslint . -o $REPORT_DIR/eslint_report.txt --ext .js || true
  else
    echo "No ESLint configuration found, skipping JavaScript linting"
  fi
fi

# =====================
# 3. EXCHANGE API CONSISTENCY
# =====================
echo -e "\n${YELLOW}Checking exchange API implementations...${NC}"

# Check for consistent exchange API implementations
if [ $PYTHON_FILES -gt 0 ]; then
  python - << EOF > $REPORT_DIR/exchange_api_consistency.txt
import glob
import re

exchange_files = glob.glob('./src/exchanges/*.py')
base_file = './src/exchanges/base_exchange.py'
required_methods = ['connect', 'get_balance', 'get_ticker', 'place_order', 'cancel_order']

findings = []

# Skip base class
for file in [f for f in exchange_files if f != base_file and not f.endswith('__init__.py')]:
  with open(file, 'r') as f:
    content = f.read()
    
  exchange_name = file.split('/')[-1].replace('.py', '')
  missing_methods = []
  
  for method in required_methods:
    if not re.search(f"def {method}\\(", content):
      missing_methods.append(method)
  
  if missing_methods:
    findings.append(f"{exchange_name}: Missing implementations for {', '.join(missing_methods)}")

if findings:
  print("Exchange API Consistency Issues:")
  for finding in findings:
    print(f"- {finding}")
else:
  print("All exchange implementations are consistent with the base class.")
EOF
fi

# =====================
# 4. TRADING STRATEGY PATTERNS
# =====================
echo -e "\n${YELLOW}Verifying trading strategy implementations...${NC}"

# Check for consistent strategy implementations
if [ $PYTHON_FILES -gt 0 ]; then
  python - << EOF > $REPORT_DIR/strategy_pattern_verification.txt
import glob
import re

strategy_files = glob.glob('./src/strategies/*.py')
base_file = './src/strategies/base_strategy.py'
required_methods = ['generate_signals', 'run']

findings = []

# Skip base class and __init__
for file in [f for f in strategy_files if f != base_file and not f.endswith('__init__.py')]:
  with open(file, 'r') as f:
    content = f.read()
    
  strategy_name = file.split('/')[-1].replace('.py', '')
  missing_methods = []
  
  for method in required_methods:
    if not re.search(f"def {method}\\(", content):
      missing_methods.append(method)
  
  if missing_methods:
    findings.append(f"{strategy_name}: Missing implementations for {', '.join(missing_methods)}")

if findings:
  print("Strategy Pattern Issues:")
  for finding in findings:
    print(f"- {finding}")
else:
  print("All strategy implementations follow the required pattern.")
EOF
fi

# =====================
# 5. PORTFOLIO RISK ANALYSIS
# =====================
echo -e "\n${YELLOW}Analyzing portfolio risk patterns...${NC}"

if [ $PYTHON_FILES -gt 0 ]; then
  python - << EOF > $REPORT_DIR/portfolio_risk_analysis.txt
import glob
import re

# Look for risk-related code patterns
issues = []

# Check for missing stop-loss implementations
strategy_files = glob.glob('./src/strategies/*.py')
for file in strategy_files:
  if file.endswith('__init__.py') or file.endswith('base_strategy.py'):
    continue
    
  with open(file, 'r') as f:
    content = f.read()
    
  strategy_name = file.split('/')[-1].replace('.py', '')
  
  # Check for stop loss implementation
  if not re.search(r'stop_loss|stoploss', content, re.IGNORECASE):
    issues.append(f"{strategy_name}: No stop-loss mechanism detected")
    
  # Check for position sizing
  if not re.search(r'position_size|risk_percentage|risk_factor', content, re.IGNORECASE):
    issues.append(f"{strategy_name}: No position sizing controls detected")

if issues:
  print("Portfolio Risk Issues:")
  for issue in issues:
    print(f"- {issue}")
else:
  print("No obvious portfolio risk issues found.")
EOF
fi

# =====================
# 6. UNUSED CODE DETECTION
# =====================
echo -e "\n${YELLOW}Looking for unused code...${NC}"

# Find unused Python code
if [ $PYTHON_FILES -gt 0 ]; then
  echo "Checking for unused Python code..."
  pip install vulture > /dev/null 2>&1 || true
  vulture . --min-confidence 80 > $REPORT_DIR/unused_python_code.txt || true
fi

# Find unused JavaScript code/dependencies
if [ $JS_FILES -gt 0 ] && [ -f "package.json" ]; then
  echo "Checking for unused JavaScript dependencies..."
  npm install -g depcheck > /dev/null 2>&1 || true
  depcheck --json > $REPORT_DIR/unused_js_dependencies.json || true
fi

# =====================
# 7. TEST COVERAGE ANALYSIS
# =====================
echo -e "\n${YELLOW}Analyzing test coverage...${NC}"

if [ $PYTHON_FILES -gt 0 ] && [ -d "tests" ]; then
  echo "Running test coverage analysis..."
  pip install pytest pytest-cov > /dev/null 2>&1 || true
  python -m pytest tests/ --cov=src --cov-report=term --cov-report=html:$REPORT_DIR/coverage_html > $REPORT_DIR/test_coverage.txt || true
fi

# =====================
# 8. PERFORMANCE CHECKS
# =====================
echo -e "\n${YELLOW}Checking for performance issues...${NC}"

# Python performance issues
if [ $PYTHON_FILES -gt 0 ]; then
  echo "Looking for Python performance issues..."
  pip install pyinstrument > /dev/null 2>&1 || true
  echo "Note: Run pyinstrument manually on specific entry points for detailed performance analysis"
fi

# =====================
# 9. FIND LARGE FILES
# =====================
echo -e "\n${YELLOW}Looking for unusually large files...${NC}"
find . -type f -not -path "*/\.*" -not -path "*/node_modules/*" -not -path "*/venv/*" -size +1M | sort -nr > $REPORT_DIR/large_files.txt

# =====================
# 10. FIND OUTDATED COMMENTS AND TODO MARKERS
# =====================
echo -e "\n${YELLOW}Finding TODO comments and potential outdated documentation...${NC}"
grep -r "TODO\|FIXME\|XXX" --include="*.py" --include="*.js" --include="*.html" . > $REPORT_DIR/todo_comments.txt || true

# =====================
# 11. CODE COMPLEXITY
# =====================
echo -e "\n${YELLOW}Analyzing code complexity...${NC}"

if [ $PYTHON_FILES -gt 0 ]; then
  echo "Checking Python code complexity..."
  pip install radon > /dev/null 2>&1 || true
  radon cc src/ -a -j > $REPORT_DIR/code_complexity.json || true
fi

# =====================
# 12. GENERATE CONSOLIDATED REPORT
# =====================
echo -e "\n${YELLOW}Generating consolidated report...${NC}"

python - << EOF > $REPORT_DIR/summary_report.md
import json
import os
import glob

summary = {
    'security_issues': 0,
    'code_quality_issues': 0,
    'exchange_consistency_issues': 0,
    'strategy_pattern_issues': 0,
    'portfolio_risk_issues': 0,
    'unused_code_count': 0,
    'test_coverage': 0,
    'high_complexity_functions': 0,
    'todos_count': 0,
    'critical_issues': []
}

report_dir = '$REPORT_DIR'

# Security issues from Python dependencies
try:
    with open(f'{report_dir}/python_security_report.txt', 'r') as f:
        content = f.read()
        if 'No known security vulnerabilities found' not in content:
            lines = content.strip().split('\n')
            summary['security_issues'] += len([l for l in lines if l.strip() and not l.startswith('=')])
            for line in [l for l in lines if l.strip() and not l.startswith('=')][:5]:
                summary['critical_issues'].append(f'Security issue: {line.strip()}')
except:
    pass

# Crypto-specific security issues
try:
    with open(f'{report_dir}/crypto_security_issues.txt', 'r') as f:
        content = f.read()
        if 'Issues:' in content:
            issues = [line.strip()[2:] for line in content.split('Issues:')[1].split('\n') if line.strip().startswith('- ')]
            summary['security_issues'] += len(issues)
            for issue in issues[:5]:
                summary['critical_issues'].append(f'Crypto security issue: {issue}')
except:
    pass

# Code quality issues
try:
    with open(f'{report_dir}/flake8_report.txt', 'r') as f:
        lines = f.readlines()
        if lines:
            try:
                summary['code_quality_issues'] += int(lines[-1].strip())
            except:
                summary['code_quality_issues'] += len(lines)
except:
    pass

# Exchange API consistency issues
try:
    with open(f'{report_dir}/exchange_api_consistency.txt', 'r') as f:
        content = f.read()
        if 'Issues:' in content:
            issues = [line.strip()[2:] for line in content.split('Issues:')[1].split('\n') if line.strip().startswith('- ')]
            summary['exchange_consistency_issues'] = len(issues)
            for issue in issues[:5]:
                summary['critical_issues'].append(f'Exchange API issue: {issue}')
except:
    pass

# Strategy pattern issues
try:
    with open(f'{report_dir}/strategy_pattern_verification.txt', 'r') as f:
        content = f.read()
        if 'Issues:' in content:
            issues = [line.strip()[2:] for line in content.split('Issues:')[1].split('\n') if line.strip().startswith('- ')]
            summary['strategy_pattern_issues'] = len(issues)
            for issue in issues[:5]:
                summary['critical_issues'].append(f'Strategy pattern issue: {issue}')
except:
    pass

# Portfolio risk issues
try:
    with open(f'{report_dir}/portfolio_risk_analysis.txt', 'r') as f:
        content = f.read()
        if 'Issues:' in content:
            issues = [line.strip()[2:] for line in content.split('Issues:')[1].split('\n') if line.strip().startswith('- ')]
            summary['portfolio_risk_issues'] = len(issues)
            for issue in issues[:5]:
                summary['critical_issues'].append(f'Portfolio risk issue: {issue}')
except:
    pass

# Unused code
try:
    with open(f'{report_dir}/unused_python_code.txt', 'r') as f:
        lines = f.readlines()
        summary['unused_code_count'] = len(lines)
except:
    pass

# Test coverage
try:
    with open(f'{report_dir}/test_coverage.txt', 'r') as f:
        content = f.read()
        coverage_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', content)
        if coverage_match:
            summary['test_coverage'] = int(coverage_match.group(1))
except:
    pass

# Code complexity
try:
    with open(f'{report_dir}/code_complexity.json', 'r') as f:
        complexity_data = json.load(f)
        high_complexity = [item for item in complexity_data if item.get('complexity', 0) > 10]
        summary['high_complexity_functions'] = len(high_complexity)
        for func in high_complexity[:5]:
            summary['critical_issues'].append(f'High complexity: {func.get("name")} ({func.get("complexity")}) in {func.get("filename")}')
except:
    pass

# TODOs count
try:
    with open(f'{report_dir}/todo_comments.txt', 'r') as f:
        lines = f.readlines()
        summary['todos_count'] = len(lines)
except:
    pass

# Write markdown report
with open(f'{report_dir}/summary_report.md', 'w') as f:
    f.write('# Crypto Trading Bot Code Analysis Summary\n\n')
    f.write(f'Generated on: {os.popen("date").read().strip()}\n\n')
    
    # Overall health score calculation
    max_score = 100
    deductions = 0
    
    if summary['security_issues'] > 0:
        deductions += min(30, summary['security_issues'] * 5)
    
    if summary['exchange_consistency_issues'] > 0:
        deductions += min(20, summary['exchange_consistency_issues'] * 5)
    
    if summary['strategy_pattern_issues'] > 0:
        deductions += min(20, summary['strategy_pattern_issues'] * 5)
    
    if summary['portfolio_risk_issues'] > 0:
        deductions += min(15, summary['portfolio_risk_issues'] * 5)
    
    if summary['test_coverage'] < 60:
        deductions += min(15, (60 - summary['test_coverage']) // 4)
    
    health_score = max(0, max_score - deductions)
    health_category = 'Excellent' if health_score >= 90 else 'Good' if health_score >= 75 else 'Fair' if health_score >= 60 else 'Poor'
    
    f.write(f'## Overall Health Score: {health_score}/100 ({health_category})\n\n')
    
    # Critical issues
    f.write('## Critical Issues\n\n')
    if not summary['critical_issues']:
        f.write('No critical issues found.\n\n')
    else:
        for issue in summary['critical_issues']:
            f.write(f'- {issue}\n')
        f.write('\n')
    
    # Security section
    f.write('## Security Analysis\n\n')
    if summary['security_issues'] == 0:
        f.write('✅ No security issues found in dependencies\n')
    else:
        f.write(f'⚠️ {summary["security_issues"]} security issues found in dependencies\n')
    
    if os.path.exists(f'{report_dir}/crypto_security_issues.txt'):
        with open(f'{report_dir}/crypto_security_issues.txt', 'r') as f:
            content = f.read()
            if 'No obvious crypto security issues found' in content:
                f.write('✅ No crypto-specific security issues found\n')
            else:
                f.write('⚠️ Crypto-specific security issues found, see crypto_security_issues.txt for details\n')
    
    # Exchange API consistency
    f.write('\n## Exchange API Consistency\n\n')
    if summary['exchange_consistency_issues'] == 0:
        f.write('✅ All exchange implementations are consistent with the base class\n')
    else:
        f.write(f'⚠️ {summary["exchange_consistency_issues"]} exchange API consistency issues found\n')
        
    # Strategy patterns
    f.write('\n## Trading Strategy Patterns\n\n')
    if summary['strategy_pattern_issues'] == 0:
        f.write('✅ All strategy implementations follow the required pattern\n')
    else:
        f.write(f'⚠️ {summary["strategy_pattern_issues"]} strategy pattern issues found\n')
    
    # Portfolio risk analysis
    f.write('\n## Portfolio Risk Analysis\n\n')
    if summary['portfolio_risk_issues'] == 0:
        f.write('✅ All strategies include risk management controls\n')
    else:
        f.write(f'⚠️ {summary["portfolio_risk_issues"]} portfolio risk issues found - missing stop-loss or position sizing\n')
    
    # Code quality
    f.write('\n## Code Quality\n\n')
    if summary['code_quality_issues'] == 0:
        f.write('✅ No code quality issues found\n')
    else:
        f.write(f'⚠️ {summary["code_quality_issues"]} code quality issues found\n')
    
    # Complexity
    if summary['high_complexity_functions'] == 0:
        f.write('✅ No high complexity functions found\n')
    else:
        f.write(f'⚠️ {summary["high_complexity_functions"]} functions with high complexity found\n')
    
    # Test coverage
    f.write('\n## Test Coverage\n\n')
    if summary['test_coverage'] >= 80:
        f.write(f'✅ Good test coverage: {summary["test_coverage"]}%\n')
    elif summary['test_coverage'] >= 60:
        f.write(f'⚠️ Moderate test coverage: {summary["test_coverage"]}%\n')
    elif summary['test_coverage'] > 0:
        f.write(f'❌ Poor test coverage: {summary["test_coverage"]}%\n')
    else:
        f.write('❌ No test coverage data available\n')
    
    # Unused code
    f.write('\n## Unused Code\n\n')
    if summary['unused_code_count'] == 0:
        f.write('✅ No unused code found\n')
    else:
        f.write(f'⚠️ {summary["unused_code_count"]} potentially unused code items found\n')
    
    # TODOs
    f.write('\n## Technical Debt\n\n')
    if summary['todos_count'] == 0:
        f.write('✅ No TODO/FIXME comments found\n')
    else:
        f.write(f'ℹ️ {summary["todos_count"]} TODO/FIXME comments found\n')
    
    # Next steps section
    f.write('\n## Recommended Actions\n\n')
    
    # Prioritize recommendations based on issues found
    recommendations = []
    
    if summary['security_issues'] > 0:
        recommendations.append('🔴 Address security vulnerabilities in dependencies')
        
    if summary['exchange_consistency_issues'] > 0:
        recommendations.append('🔴 Fix exchange API inconsistencies to ensure all exchanges implement required methods')
        
    if summary['strategy_pattern_issues'] > 0:
        recommendations.append('🔴 Fix strategy implementation issues to ensure all required methods are implemented')
        
    if summary['portfolio_risk_issues'] > 0:
        recommendations.append('🔴 Implement missing risk controls (stop-loss, position sizing) in trading strategies')
    
    if summary['code_quality_issues'] > 10:
        recommendations.append('🟠 Address code quality issues to improve maintainability')
    
    if summary['high_complexity_functions'] > 0:
        recommendations.append('🟠 Refactor high complexity functions to improve readability and testability')
    
    if summary['test_coverage'] < 60:
        recommendations.append('🟠 Improve test coverage, especially for critical components')
    
    if summary['unused_code_count'] > 10:
        recommendations.append('🟡 Clean up unused code to reduce maintenance burden')
    
    if not recommendations:
        f.write('✅ No critical issues to address\n')
    else:
        for rec in recommendations:
            f.write(f'- {rec}\n')
EOF

echo -e "${GREEN}Analysis complete! Reports are available in the $REPORT_DIR directory${NC}"
echo -e "${YELLOW}Main summary report: $REPORT_DIR/summary_report.md${NC}"

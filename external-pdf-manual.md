Created crypto-agent-pdf-prompt.md in the project root.

How to use it in Claude UI:
1. Add crypto-agent-pdf-prompt.md as a project prompt / system instruction in Claude Design
2. Paste the full MD report from /dart into the chat
3. Claude outputs a JSON code block
4. Save that JSON to a file and run:
   python3 scripts/generate_english_pdf.py input.json output.pdf

The prompt handles all the translation rules: BTC Watch (both qualified and watch modes), top 3 non-BTC coins, open positions with the 10-hour privacy filter and beginner-friendly action translations, market mood, and daily
conclusion — same output as /englishfeed produces.
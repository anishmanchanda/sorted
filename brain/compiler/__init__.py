"""The ability compiler: repeated LLM work -> tested, versioned local code.

detector     groups accepted LLM traces and creates candidates
generator    compiler agent (strong LLM route) writes the parser, then static check + sandbox tests
static_check AST allowlist for generated code
sandbox      runs generated code in a separate, network-less subprocess with a timeout
registry     lifecycle: match / execute / shadow / activate / degrade / approve
"""

import asyncio
import logging
import re
from typing import List, Dict, Any


logger = logging.getLogger(__name__)


async def run_maigret(username: str) -> str:
    try:
        process = await asyncio.create_subprocess_exec(
            'maigret', username[1:],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, _ = await process.communicate()
        raw_output = stdout.decode('utf-8', errors='ignore')

        lines = raw_output.splitlines()
        result_lines = []
        capture = False
        current_block = []

        for line in lines:
            stripped = line.strip()
            
            if (stripped.startswith('[-]') or 
                stripped.startswith('[!]') or 
                stripped.startswith('[*]') or 
                stripped.startswith('[?]') or
                'Searching' in line or '|' in line):    
                continue

            if line.lstrip().startswith('[+]'):
                if current_block:
                    result_lines.extend(current_block)
                    result_lines.append("")  
                    current_block = []
                capture = True
                current_block.append(line) 
                continue

        
            if capture and (line.startswith('        ├─') or line.startswith('        └─')):
                current_block.append(line)
            else:
                
                if capture and line and not line.startswith('        '):
                    result_lines.extend(current_block)
                    result_lines.append("")
                    current_block = []
                    capture = False

        if current_block:
            result_lines.extend(current_block)
            result_lines.append("")

        if not result_lines:
            result_lines.append("No accounts found.")
            pass
        return "\n".join(result_lines).rstrip() + "\n"

    except Exception as e:
        logger.error(f"Error running Maigret: {e}")
        return "An error occurred while performing the search."

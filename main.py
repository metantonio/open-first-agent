import asyncio
import logging
import sys
import traceback
from agents import Runner
from cigar_agents.orchestrator_agent import orchestrator_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('cigar_scraper.log')
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Main function to run the cigar comparison script."""
    logger.info("\n=== Starting cigar comparison script ===")
    
    try:
        # Get the brand to search for
        brand = input("Enter the cigar brand to compare: ").strip()
        if not brand:
            logger.error("Brand name cannot be empty")
            return
        
        # Run the orchestrator agent using Runner
        result = await Runner.run(
            orchestrator_agent,
            input=f"Compare cigars of the brand '{brand}' between mikescigars.com and cigars.com. Save the results to JSON with today's date, then convert to CSV."
        )
        
        logger.info("\n=== Script completed successfully ===")
        
    except Exception as e:
        logger.error(f"\nUnexpected error during execution: {str(e)}")
        logger.error(traceback.format_exc())
    
    finally:
        logger.info("\n=== Script completed ===")

if __name__ == "__main__":
    asyncio.run(main())
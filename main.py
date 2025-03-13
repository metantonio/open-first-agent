import asyncio
import logging
import sys
import traceback
import json
from agents import Runner
from cigar_agents.orchestrator_agent import orchestrator_agent
from cigar_agents.html_parser_agent import html_parser_agent
from cigar_agents.export_agents import all_products_agent

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
        agents_result = await Runner.run(
            orchestrator_agent,
            input=f"Compare cigars of the brand '{brand}' between mikescigars.com and cigars.com. Save the results to JSON with today's date, then convert to CSV."
        )

        # Process scraper results
        raw_result = agents_result.final_output
        logger.info("Debug - Raw scraper output: %s", raw_result)
        
        # Initialize variables with empty lists
        mikes_products = []
        cigars_products = []
        matches = []
        
        try:
            # Clean up the raw output if it contains markdown
            if isinstance(raw_result, str):
                # Remove markdown code blocks if present
                raw_result = raw_result.replace('```json\n', '').replace('```\n', '').replace('```', '')
                raw_result = raw_result.strip()
                # Remove any "Here is..." prefix text
                if raw_result.startswith('Here is'):
                    raw_result = raw_result[raw_result.find('{'):]
                raw_result = json.loads(raw_result)
            
            # Ensure we have a dictionary
            if isinstance(raw_result, dict):
                # Check for both possible key names for matches
                required_keys = ['mikes_products', 'cigars_products']
                matches_key = 'matches' if 'matches' in raw_result else 'matched_products'
                required_keys.append(matches_key)
                
                if not all(key in raw_result for key in required_keys):
                    raise ValueError(f"Missing required keys in scraper result. Required: {required_keys}")
                
                # Update our variables
                mikes_products = raw_result['mikes_products']
                cigars_products = raw_result['cigars_products']
                matches = raw_result[matches_key]
                
                if not isinstance(mikes_products, list) or not isinstance(cigars_products, list):
                    raise ValueError("Products must be lists")
                
                logger.info("Validated scraper results:")
                logger.info(f"- Found {len(mikes_products)} Mike's Cigars products")
                logger.info(f"- Found {len(cigars_products)} Cigars.com products")
                logger.info(f"- Found {len(matches)} matching products")
            else:
                raise ValueError(f"Unexpected scraper result type: {type(raw_result)}")
            
        except Exception as e:
            logger.error(f"Error processing scraper results: {str(e)}")
            # Variables already initialized with empty lists
        
        # Run the HTML Parser Agent
        logger.info("\n=== Running HTML Parser Agent ===")
        parser_result = await Runner.run(
            html_parser_agent,
            input=f"Parse HTML and extract detailed product information for the brand '{brand}'. Execute the parsing functions in order and return a properly formatted JSON object with the results."
        )
        logger.info("\nHTML Parser Agent completed")
        
        # Process HTML Parser results
        try:
            parser_output = parser_result.final_output
            if isinstance(parser_output, str):
                # Clean up the raw output if it contains markdown
                parser_output = parser_output.replace('```json\n', '').replace('```\n', '').replace('```', '')
                parser_output = parser_output.strip()
                # Remove any "Here is..." prefix text
                if parser_output.startswith('Here is'):
                    parser_output = parser_output[parser_output.find('{'):]
                parser_output = json.loads(parser_output)
            
            if isinstance(parser_output, dict):
                required_keys = ['mikes_detailed_products', 'cigars_detailed_products', 'detailed_csv_file']
                if not all(key in parser_output for key in required_keys):
                    raise ValueError(f"Missing required keys in parser result. Required: {required_keys}")
                
                logger.info("HTML Parser found:")
                logger.info(f"- {len(parser_output['mikes_detailed_products'])} detailed products from Mike's Cigars")
                logger.info(f"- {len(parser_output['cigars_detailed_products'])} detailed products from Cigars.com")
                logger.info(f"- Saved detailed products to: {parser_output['detailed_csv_file']}")
            else:
                raise ValueError(f"Unexpected parser result type: {type(parser_output)}")
            
        except Exception as e:
            logger.error(f"Error processing HTML Parser results: {str(e)}")
            # Keep the initialized empty dictionary
        

        # Run the All Products Export Agent
        logger.info("\n=== Running All Products Export Agent ===")
        try:
            # Use validated products from scraper
            all_products_result = await Runner.run(
                all_products_agent,
                input=json.dumps({
                    "brand": brand,
                    "mikes_products": mikes_products,
                    "cigars_products": cigars_products
                })
            )
            logger.info("\nAll Products Export Agent completed")
            
        except Exception as e:
            logger.error(f"Error in final processing: {str(e)}")
            raise

        logger.info("\n=== Script completed successfully ===")
        
    except Exception as e:
        logger.error(f"\nUnexpected error during execution: {str(e)}")
        logger.error(traceback.format_exc())
    
    finally:
        logger.info("\n=== Script completed ===")

if __name__ == "__main__":
    asyncio.run(main())
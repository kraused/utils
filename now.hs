
import System.Environment
import System.Locale
import Data.Time
import Data.Time.Format
import Data.Time.LocalTime

formatString :: [String] -> String
formatString ["-f"] = "%Y-%m-%dT%H%M%SZ%z"
formatString _      = "%Y-%m-%d"

main :: IO ()
main = do
	 now  <- getCurrentTime >>= utcToLocalZonedTime
	 args <- getArgs
         putStrLn $ formatTime defaultTimeLocale (formatString args) now


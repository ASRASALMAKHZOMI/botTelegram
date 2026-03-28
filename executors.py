from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=15)
coding_executor = ThreadPoolExecutor(max_workers=6)
explanation_executor = ThreadPoolExecutor(max_workers=4)
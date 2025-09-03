import frappe

@frappe.whitelist()
def get_progress(progress_key):
    progress_data = frappe.cache().get_value(progress_key)

    # if not progress_data:
    #     frappe.logger().warning(f"Progress key {progress_key} not found in cache.")
    #     return {
    #         "progress": 100,
    #         "total_success_item": 0,
    #         "total_fail_item": 0,
    #         "total_found_item": 0,
    #         "final_item_list": [],
    #         "flag_complete": False,
    #         "message": "No backend function is running"
    #     }
    
    return progress_data

def setup_progress_id():
    progress_key = frappe.generate_hash(length=10)
    return progress_key

class ProgressTracker:
    ## Generic Progress Tracker Class ##
    def __init__(self, progress_id):
        self.progress_id = progress_id
        self.progress = 0
        self.total_items = 0
        self.success_count = 0
        self.fail_count = 0
        self.process_count = 0
        self.processed_items = []
        self.is_complete = False
        self.message = "Processing started."

    def set_total_items(self, total):
        ## Setup total item need to be processed ##
        self.total_items = total

    def update_progress(self, success=True, item=None):
        ## Update and append success item list ##
        ## Update counter ##
        if self.total_items == 0:
            frappe.logger().warning(f"Total items not set for progress_id {self.progress_id}")
            return

        self.process_count += 1
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1
        
        if item:
            self.processed_items.append(item)
            
        self.progress = min(int((self.process_count) / self.total_items * 100),100)
        self.message = f"{self.progress}%. {self.process_count} items had proccessed..."
        self._save()

    def mark_complete(self, message="Processing complete."):
        ## If all item had been processed, complete the item list ##
        ## You also can call this function to force closed and put a message here ##
        self.is_complete = True
        self.message = message
        self._save()

    def _save(self):
        ## Update in cache, so front end can prompt the value ##
        ## The value will be expired in one days ##
        frappe.cache().set_value(self.progress_id, self.to_dict(), expires_in_sec=86400)
    
    def to_dict(self):
        ## Convert the tracker state to a dictionary ##
        return {
            "progress": self.progress,
            "total_items": self.total_items,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "process_count": self.process_count,
            "processed_items": self.processed_items,
            "is_complete": self.is_complete,
            "message": self.message
        }
    
    def get_progress_percentage(self):
        return self.progress

    def stop_complete_error(self, message="Please try again later in few seconds. Rate Limit Exceeded for API call \n"):
        self.is_complete = True
        self.message = message
        self.progress = 100
        self._save()

class StopExecution(Exception):
    pass
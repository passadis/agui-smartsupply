-- Use this script to initialize your Azure SQL Database

CREATE TABLE Orders (
    OrderID NVARCHAR(50) PRIMARY KEY,
    Status NVARCHAR(50),
    Priority NVARCHAR(50),
    Category NVARCHAR(50),
    OrderPhotoUrl NVARCHAR(2048) NULL,
    DeliveryAddress NVARCHAR(512) NULL,
    Remarks NVARCHAR(2048) NULL
);

-- Insert Sample Data
INSERT INTO Orders (OrderID, Status, Priority, Category) VALUES
('9921', 'Delayed', 'Standard', 'Hazardous'),
('1234', 'Shipped', 'Standard', 'Apparel'),
('5678', 'Processing', 'High', 'Electronics'),
('9101', 'Delivered', 'Low', 'Books'),
('1121', 'Cancelled', 'Standard', 'Furniture'),
('3141', 'Processing', 'High', 'Toys'),
('5161', 'Shipped', 'Low', 'Groceries');


-- Verify
SELECT * FROM Orders;

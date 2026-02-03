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
INSERT INTO Orders (
    OrderID, Status, Priority, Category, OrderPhotoUrl, DeliveryAddress, Remarks
) VALUES
('1045','Shipped','Low','Electronics','https://<yourblobstorage>.blob.core.windows.net/orderpics/order_1045.jpg',NULL,NULL),
('1086','Delayed','High','Furniture',NULL,NULL,NULL),
('2048','Delivered','Standard','Furniture',NULL,NULL,NULL),
('2197','Delivered','Standard','Clothing',NULL,NULL,NULL),
('3189','Cancelled','High','Perishable',NULL,NULL,NULL),
('3308','On Hold','Low','Automotive',NULL,NULL,NULL),
('4277','Processing','Low','Clothing',NULL,NULL,NULL),
('4419','Shipped','High','Fragile','https://<yourblobstorage>.blob.core.windows.net/orderpics/order_4419.jpg',NULL,NULL),
('5390','Shipped','High','Hazardous','https:/<yourblobstorage>.blob.core.windows.net/orderpics/order_5390.jpg',NULL,NULL),
('5520','Cancelled','Low','Hazardous',NULL,NULL,NULL),
('6321','Processing','High','Fragile',NULL,NULL,NULL),
('6482','Delivered','Low','Fragile',NULL,NULL,NULL),
('6631','Processing','Standard','Electronics',NULL,NULL,NULL),
('7593','Shipped','Standard','Automotive',NULL,NULL,NULL),
('7742','Delivered','High','Perishable',NULL,NULL,NULL),
('8604','Returned','High','Electronics',NULL,NULL,NULL),
('8853','Returned','Standard','Furniture',NULL,NULL,NULL),
('9715','Processing','Standard','Perishable',NULL,NULL,NULL),
('9921','Delayed','Standard','Hazardous',NULL,NULL,NULL),
('9964','Shipped','Low','Clothing',NULL,NULL,NULL),

('A1001','Delayed','High','Fragile',NULL,'45 Marble Ave., Athens 115 24',
 'Wrong address, correct address is New Query Str. 122, Athens 112 77'),

('A1002','Shipped','Standard','Electronics',NULL,'12 Ionias Str., Piraeus 185 45',
 'Correct address'),

('A1003','Processing','Low','Hazardous',NULL,'New Query Str. 222, Athens 112 77',
 'RESOLVED: Wrong address corrected. DeliveryAddress updated to: New Query Str. 222, Athens 112 77. Status set to Processing.

Previous remarks (for audit):
Wrong address, correct address is New Query Str. 222, Athens 112 77'),

('A1004','On Hold','High','Fragile',NULL,'19 Artemis Blvd., Patra 262 22',
 'Recipient unavailable'),

('A1005','Returned','Standard','Electronics',NULL,'5 Green Park Lane, Athens 114 72',
 'Wrong address provided by customer'),

('A1006','Processing','Low','Hazardous',NULL,'33 Horizon Str., Heraklion 713 05',
 'Correct address'),

('A1007','Returned','High','Fragile',NULL,'90 Blue Harbor Ave., Volos 382 21',
 'Wrong address, correct address is New Vent Str. 222, Athens 112 77'),

('A1008','Shipped','Standard','Electronics',NULL,'14 Olive Grove Str., Athens 117 43',
 'Correct address'),

('A1009','Cancelled','Low','Hazardous',NULL,'22 Mountain View Rd., Larisa 412 22',
 'Order cancelled before dispatch'),

('A1010','Delayed','High','Fragile',NULL,'7 Riverstone Str., Chania 731 33',
 'Wrong address, correct address is New Rent Str. 22, Athens 112 77');


-- Verify
SELECT * FROM Orders;

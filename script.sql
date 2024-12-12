
CREATE DATABASE EventHive;

use EventHive;

-- 1. Users Table
CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL, 
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE UserSessions (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    logged_in_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    logged_out_at DATETIME DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);


-- 2. Events Table
CREATE TABLE Events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    street VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    views INT NOT NULL DEFAULT 0,
    tags VARCHAR(255),
    created_by INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES Users(user_id)
);


-- 3. Pricing_Tiers Table
CREATE TABLE Pricing_Tiers (
    tier_id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    tier_name VARCHAR(255) NOT NULL,
    tier_description TEXT NULL,
    price DECIMAL(10, 2) NOT NULL,
    available_tickets INT NOT NULL,
    total_tickets_sold INT DEFAULT 0,
    FOREIGN KEY (event_id) REFERENCES Events(event_id)
);

-- 4. Event_Media Table
CREATE TABLE Event_Media (
    media_id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    media_url TEXT NOT NULL,
    media_type ENUM('image', 'video') NOT NULL,
    sequence INT NULL,
    FOREIGN KEY (event_id) REFERENCES Events(event_id)
);

-- 5. Bookings Table
CREATE TABLE Bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    event_id INT NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    booking_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (event_id) REFERENCES Events(event_id)
);

-- 6. Booking_Details Table
CREATE TABLE Booking_Details (
    booking_id INT NOT NULL,
    tier_id INT NOT NULL,
    quantity INT NOT NULL,
    price_per_ticket DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (booking_id) REFERENCES Bookings(booking_id),
    FOREIGN KEY (tier_id) REFERENCES Pricing_Tiers(tier_id),
    CONSTRAINT pk_booking_details PRIMARY KEY (booking_id, tier_id)
);

ALTER TABLE Events
ADD image_path VARCHAR(250);


-- ============================================================================
--  EstateDB  |  06_seed.sql (Bangla / বাংলাদেশ সংস্করণ)
--  Sample data for every table in Bengali context.
--
--  Two ID strategies are demonstrated on purpose:
--    * Tables that are FK targets (roles, cities, types, amenities, users,
--      agents, properties, images) get EXPLICIT ids so the relationships below
--      are easy to read. MySQL AUTO_INCREMENT automatically tracks the maximum.
--    * INQUIRIES, TRANSACTIONS and REVIEWS omit their id and let AUTO_INCREMENT
--      assign it.
--
--  Note also that properties 17-21 and 23 are inserted as AVAILABLE; the
--  TRANSACTIONS inserts near the bottom flip them to SOLD/RENTED via
--  trg_txn_after_insert_status, and their commission is filled in by
--  trg_txn_before_insert.
--  The audit_log rows are likewise produced automatically by the triggers.
-- ============================================================================

-- ----------------------------------------------------------------------------
--  Lookup data (শহর, প্রপার্টির ধরন, সুযোগ-সুবিধা)
-- ----------------------------------------------------------------------------
INSERT INTO roles (role_id, role_name) VALUES (1, 'Admin');
INSERT INTO roles (role_id, role_name) VALUES (2, 'Agent');
INSERT INTO roles (role_id, role_name) VALUES (3, 'Customer');

INSERT INTO cities (city_id, city_name, state, country) VALUES (1, 'ঢাকা',       'ঢাকা',       'বাংলাদেশ');
INSERT INTO cities (city_id, city_name, state, country) VALUES (2, 'চট্টগ্রাম',   'চট্টগ্রাম',   'বাংলাদেশ');
INSERT INTO cities (city_id, city_name, state, country) VALUES (3, 'সিলেট',      'সিলেট',      'বাংলাদেশ');
INSERT INTO cities (city_id, city_name, state, country) VALUES (4, 'কক্সবাজার',   'চট্টগ্রাম',   'বাংলাদেশ');
INSERT INTO cities (city_id, city_name, state, country) VALUES (5, 'রাজশাহী',    'রাজশাহী',    'বাংলাদেশ');
INSERT INTO cities (city_id, city_name, state, country) VALUES (6, 'খুলনা',      'খুলনা',      'বাংলাদেশ');
INSERT INTO cities (city_id, city_name, state, country) VALUES (7, 'বরিশাল',     'বরিশাল',     'বাংলাদেশ');
INSERT INTO cities (city_id, city_name, state, country) VALUES (8, 'রংপুর',      'রংপুর',      'বাংলাদেশ');

INSERT INTO property_types (type_id, type_name) VALUES (1, 'বাড়ি');
INSERT INTO property_types (type_id, type_name) VALUES (2, 'অ্যাপার্টমেন্ট');
INSERT INTO property_types (type_id, type_name) VALUES (3, 'কনডোমিনিয়াম');
INSERT INTO property_types (type_id, type_name) VALUES (4, 'ভিলা / বাংলো');
INSERT INTO property_types (type_id, type_name) VALUES (5, 'টাউনহাউস');
INSERT INTO property_types (type_id, type_name) VALUES (6, 'বাণিজ্যিক স্পেস');

INSERT INTO amenities (amenity_id, amenity_name) VALUES (1,  'সুইমিং পুল');
INSERT INTO amenities (amenity_id, amenity_name) VALUES (2,  'গ্যারেজ পার্কিং');
INSERT INTO amenities (amenity_id, amenity_name) VALUES (3,  'বাগান');
INSERT INTO amenities (amenity_id, amenity_name) VALUES (4,  'ফিটনেস জিম');
INSERT INTO amenities (amenity_id, amenity_name) VALUES (5,  'প্রশস্ত বারান্দা');
INSERT INTO amenities (amenity_id, amenity_name) VALUES (6,  'স্ট্যান্ডবাই জেনারেটর');
INSERT INTO amenities (amenity_id, amenity_name) VALUES (7,  'আধুনিক লিফট');
INSERT INTO amenities (amenity_id, amenity_name) VALUES (8,  'সার্বক্ষণিক নিরাপত্তা');
INSERT INTO amenities (amenity_id, amenity_name) VALUES (9,  'সিসিটিভি ক্যামেরা');
INSERT INTO amenities (amenity_id, amenity_name) VALUES (10, 'গ্যাস সংযোগ');
INSERT INTO amenities (amenity_id, amenity_name) VALUES (11, 'খেলার মাঠ');
INSERT INTO amenities (amenity_id, amenity_name) VALUES (12, 'ছাদ বাগান');

-- ----------------------------------------------------------------------------
--  Users (ব্যবহারকারীগণ)
--  Plain-text passwords for the demo:
--     admin                        -> Admin@123
--     sarah / mike / lisa / david  -> Agent@123
--     john / emma / alex / olivia  -> User@123
-- ----------------------------------------------------------------------------
INSERT INTO users (user_id, username, email, password_hash, password_salt, full_name, phone, role_id) VALUES (1, 'admin', 'admin@estatedb.com', 'bb0b425a1227ac8551eddc3cbd0ab2005a4bb394eb9e8de9563cc11099353dec', '1030e3fc0a8e8ed087cb702e3585059e', 'সিস্টেম অ্যাডমিন', '01711000100', 1);
INSERT INTO users (user_id, username, email, password_hash, password_salt, full_name, phone, role_id) VALUES (2, 'sarah', 'sarah@estatedb.com', '3b1033e90ef28e633288317629114935bdfe6e27443acbf8cd0c76bc09a4b764', 'af7d05b65a4ce6d126208427899c59b4', 'সাদিয়া ইসলাম', '01812000201', 2);
INSERT INTO users (user_id, username, email, password_hash, password_salt, full_name, phone, role_id) VALUES (3, 'mike', 'mike@estatedb.com', 'b78d158c652cc51e8763407114b39278d1f53de4a8140dda13bacb9e9d19fec7', '33fcdc821cb238e8eeac426e5714bd26', 'তানভীর আহমেদ', '01713000202', 2);
INSERT INTO users (user_id, username, email, password_hash, password_salt, full_name, phone, role_id) VALUES (4, 'lisa', 'lisa@estatedb.com', '29cee6c656ed60de8b695e23712e191eb6359ea10ec9a81ee5d265682dddfbc6', '306b0784be06ff34ca1a2c6926443162', 'নুসরাত জাহান', '01914000203', 2);
INSERT INTO users (user_id, username, email, password_hash, password_salt, full_name, phone, role_id) VALUES (5, 'david', 'david@estatedb.com', '60284d811b802ac76cc5a6b45b9351e1d6608211abceae8253938e71745de3df', '2ddf9fce4b9c138efc70ab38ca21e518', 'আরিফুল হক', '01615000204', 2);
INSERT INTO users (user_id, username, email, password_hash, password_salt, full_name, phone, role_id) VALUES (6, 'john', 'john@example.com', '835865a76c3fe1af6c2c90ca5ea2d50f040fe992555412edbf69b8ebeb50430e', 'a2ce263b23f1cbad340c19a65f600f2d', 'কামাল হোসেন', '01726000301', 3);
INSERT INTO users (user_id, username, email, password_hash, password_salt, full_name, phone, role_id) VALUES (7, 'emma', 'emma@example.com', 'b7723c87ef056e02653fc61c84f96cd05c94a8bf1a6be7dc59cbecd4cd4fc4f3', 'c7e4cbae39c5d612b34c7577aab6ccb6', 'ফারহানা রহমান', '01827000302', 3);
INSERT INTO users (user_id, username, email, password_hash, password_salt, full_name, phone, role_id) VALUES (8, 'alex', 'alex@example.com', 'be9a2c9d820dfa489772d581de5980bc1c0820fa6efe4da963a67afcd3b391f9', '433159f07da515a367e3d4bd2b60e01c', 'মেহরাব হাসান', '01928000303', 3);
INSERT INTO users (user_id, username, email, password_hash, password_salt, full_name, phone, role_id) VALUES (9, 'olivia', 'olivia@example.com', '36981dc13d702a39b788e8b5415a83c1653a91864a23c93b528184d82ce0b99d', 'd35904142c88244de49ad8e7bb90a4be', 'সুমাইয়া চৌধুরী', '01529000304', 3);

-- ----------------------------------------------------------------------------
--  Agents (এজেন্টদের বিবরণ)
-- ----------------------------------------------------------------------------
INSERT INTO agents (agent_id, license_no, agency_name, bio, commission_rate, hire_date)
VALUES (2, 'BD-RE-40192', 'প্রাইম প্রোপার্টিজ বাংলাদেশ',
        'সাদিয়া ঢাকা ও চট্টগ্রামের আবাসিক প্রপার্টিতে দক্ষ এবং প্রথমবার বাড়ি ক্রেতাদের আন্তরিক পরামর্শ দিয়ে থাকেন।',
        2.50, '2018-04-16');

INSERT INTO agents (agent_id, license_no, agency_name, bio, commission_rate, hire_date)
VALUES (3, 'BD-RE-88231', 'গ্রিন সিটি রিয়েল এস্টেট',
        'তানভীর ঢাকার কনডোমিনিয়াম এবং বাণিজ্যিক প্রপার্টি বিনিয়োগের বিশ্বস্ত পরামর্শক।',
        3.00, '2016-09-01');

INSERT INTO agents (agent_id, license_no, agency_name, bio, commission_rate, hire_date)
VALUES (4, 'BD-RE-55710', 'সোনার বাংলা হাউজিং',
        'নুসরাত আধুনিক ফ্যামিলি অ্যাপার্টমেন্ট ও টাউনহাউস নিয়ে কাজ করেন এবং স্বচ্ছ চুক্তি বাস্তবায়নে সুনামধারী।',
        2.75, '2019-01-22');

INSERT INTO agents (agent_id, license_no, agency_name, bio, commission_rate, hire_date)
VALUES (5, 'BD-RE-30455', 'বেঙ্গল ভিউ রিয়েলটি',
        'আরিফুল কক্সবাজার ও চট্টগ্রামের বিলাসবহুল ভিলা এবং হলিডে রিসোর্ট প্রপার্টি কেনাবেচায় বিশেষজ্ঞ।',
        3.25, '2020-06-08');

-- ----------------------------------------------------------------------------
--  Properties (প্রপার্টি লিস্টিং)
-- ----------------------------------------------------------------------------
INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (1, 'গুলশানে আলিশান ফ্যামিলি হাউস', 'একটি শান্ত অভিজাত এলাকায় ৪ বেডের দৃষ্টিনন্দন বাড়ি। ওপেন কিচেন, সুবিশাল লিভিং রুম এবং খোলামেলা বারান্দাসহ ২০২১ সালে সম্পূর্ণ আধুনিকায়ন করা হয়েছে।', 1, 1, 2, 'বাড়ি ১২, রোড ৫, গুলশান-২, ঢাকা', 68500000, 4, 3, 2850, 2015, 'SALE', 'AVAILABLE', 'Y', NOW() - INTERVAL '120 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (2, 'মতিঝিলে মডার্ন গ্লাস লফট', 'বাণিজ্যিক এলাকার কাছে নবম তলার খোলামেলা ২ বেডের আধুনিক লফট। ছাদের বাগান এবং সর্বাধুনিক নাগরিক সুবিধা সংবলিত।', 2, 1, 2, '৭৭ দিলকুশা বাণিজ্যিক এলাকা, ইউনিট ৯০২, ঢাকা', 65000, 2, 2, 1200, 2019, 'RENT', 'AVAILABLE', 'N', NOW() - INTERVAL '95 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (3, 'কক্সবাজারে বিচভিউ বিলাসবহুল ভিলা', 'সমুদ্রের মনোরম দৃশ্য সংবলিত ৫ বেডের নান্দনিক আর্কিটেকচারাল ভিলা। সুইমিং পুল, হোম থিয়েটার এবং আলাদা গেস্ট হাউজ সুবিধা।', 4, 4, 3, '৮ মেরিন ড্রাইভ রোড, কক্সবাজার', 145000000, 5, 5, 4600, 2021, 'SALE', 'AVAILABLE', 'Y', NOW() - INTERVAL '60 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (4, 'উত্তরায় অভিজাত টাউনহাউস', 'শান্ত ও সুরক্ষিত আবাসিক এলাকায় ৩ বেডের রুচিশীল টাউনহাউস। সার্বক্ষণিক নিরাপত্তা, গাড়ি পার্কিং ও সুন্দর ছাদবাগান।', 5, 1, 4, 'প্লট ২১৫, সেক্টর ৭, উত্তরা, ঢাকা', 42500000, 3, 3, 1850, 2012, 'SALE', 'AVAILABLE', 'N', NOW() - INTERVAL '150 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (5, 'সিলেটে স্কাইভিউ কর্নার কনডো', '২২ তলার ওপর থেকে সুরমা নদী ও সবুজ পাহাড়ের নয়নাভিরাম দৃশ্য। সার্বক্ষণিক জেনারেটর, জিম ও সুপরিসর পার্কিং।', 3, 3, 3, '১৯০০ দরগাহ গেট রোড, ইউনিট ২২৪, সিলেট', 78000000, 2, 2, 1400, 2018, 'SALE', 'AVAILABLE', 'Y', NOW() - INTERVAL '45 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (6, 'রংপুরে বাগানবাড়ি ও শান্ত কটেজ', 'ফলদ ও বনজ বৃক্ষে ঘেরা ৩ বেডের পরিপাটি বাগানবাড়ি। ব্যক্তিগত স্টুডিও ও নিঝুম পরিবেশ।', 1, 8, 5, '৩৪ পার্ক রোড, রংপুর', 18500000, 3, 2, 1650, 2005, 'SALE', 'AVAILABLE', 'N', NOW() - INTERVAL '200 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (7, 'বরিশালে কমার্শিয়াল অফিস স্পেস', '২৫-৩০ জন কর্মী বসার উপযোগী ওপেন-প্ল্যান বাণিজ্যিক ফ্লোর। দুটি কনফারেন্স রুম, প্যান্ট্রি ও আধুনিক লিফট সুবিধা।', 6, 7, 2, '৫২ সদর রোড, তৃতীয় তলা, বরিশাল', 55000, 0, 2, 3200, 2010, 'RENT', 'AVAILABLE', 'N', NOW() - INTERVAL '80 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (8, 'চট্টগ্রাম খুলশীতে পাহাড়ঘেরা ডুপ্লেক্স', 'খুলশী হিলস এলাকার মনোমুগ্ধকর পরিবেশে ৪ বেডের বিলাসবহুল বাড়ি। ডাবল হাইট সিলিং ও ওপেন টেরেস।', 1, 2, 4, '৯৯০ জাকির হোসেন রোড, দক্ষিণ খুলশী, চট্টগ্রাম', 92500000, 4, 4, 3400, 2020, 'SALE', 'AVAILABLE', 'Y', NOW() - INTERVAL '35 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (9, 'খুলনায় আধুনিক স্টুডিও অ্যাপার্টমেন্ট', 'সব আধুনিক ফিটিংসহ ছোট পরিবারের জন্য আদর্শ ১ বেডের স্টুডিও ফ্ল্যাট। পানি ও বিদ্যুৎ বিল ভাড়ার অন্তর্ভুক্ত।', 2, 6, 5, '৪১০ খান জাহান আলী রোড, খুলনা', 22000, 1, 1, 620, 2016, 'RENT', 'AVAILABLE', 'N', NOW() - INTERVAL '110 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (10, 'বরিশাল নদীপাড়ে ঐতিহ্যবাহী বাড়ি', 'ঐতিহ্যবাহী নকশায় তৈরি চার তলা আবাসিক ভবন। আধুনিক ফিটিংসহ পরিপাটিভাবে সাজানো।', 5, 7, 3, '১১৮ বেলস পার্ক রোড, বরিশাল', 38000000, 4, 3, 3100, 1998, 'SALE', 'AVAILABLE', 'N', NOW() - INTERVAL '175 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (11, 'কক্সবাজার সমুদ্রসৈকতে এক্সক্লুসিভ ভিলা', 'সরাসরি সৈকতে প্রবেশের সুবিধাসহ ৬ বেডের রাজকীয় ভিলা। প্রাইভেট পুল, বারবিকিউ কর্নার ও সুবিশাল ব্যালকনি।', 4, 4, 2, '৩ কলাতলী বিচ রোড, কক্সবাজার', 210000000, 6, 6, 5800, 2022, 'SALE', 'AVAILABLE', 'Y', NOW() - INTERVAL '25 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (12, 'রাজশাহীতে পদ্মাভিউ রেসিডেনশিয়াল ফ্ল্যাট', 'পদ্মা নদীর মনোরম দৃশ্য সংবলিত ২ বেডের আলো-বাতাসপূর্ণ অ্যাপার্টমেন্ট। সুপরিসর ব্যালকনি ও সার্বক্ষণিক জেনারেটর।', 2, 5, 4, '৬০০ পদ্মা আবাসিক এলাকা, ফ্ল্যাট ১২বি, রাজশাহী', 32000, 2, 2, 1300, 2014, 'RENT', 'AVAILABLE', 'N', NOW() - INTERVAL '70 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (13, 'খুলনা সোনাডাঙ্গায় মনোরম বাড়ি', 'শান্ত আবাসিক এলাকায় ৩ বেডের একতলা সুন্দর বাড়ি। ব্যক্তিগত বাগান ও প্রশস্ত কার পার্কিং।', 1, 6, 5, '৭ সোনাডাঙা আবাসিক এলাকা, খুলনা', 28500000, 3, 2, 1720, 2008, 'SALE', 'AVAILABLE', 'N', NOW() - INTERVAL '140 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (14, 'বনানীতে প্রেসিডেন্সিয়াল পেন্টহাউস', 'পুরো ফ্লোরজুড়ে অবস্থিত লাক্সারি পেন্টহাউস। প্রাইভেট লিফট অ্যাক্সেস, বিশাল ছাদবাগান এবং আধুনিক সুযোগ-সুবিধা।', 3, 1, 3, '৫ কামাল আতাতুর্ক এভিনিউ, বনানী, ঢাকা', 187500000, 3, 3, 2600, 2023, 'SALE', 'AVAILABLE', 'Y', NOW() - INTERVAL '15 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (15, 'রংপুর ধাপ এলাকায় ইনভেস্টমেন্ট ডুপ্লেক্স', 'ভাড়ার জন্য অত্যন্ত উপযোগী দুটি পৃথক ইউনিটযুক্ত ডুপ্লেক্স বাড়ি। বিদ্যুৎ ও গ্যাস সংযোগ পৃথক।', 5, 8, 4, '২৮১ ধাপ রোড, রংপুর', 34500000, 4, 2, 2000, 1998, 'SALE', 'AVAILABLE', 'N', NOW() - INTERVAL '190 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (16, 'কক্সবাজার মেইন রোডে শোরুম স্পেস', 'প্রধান সড়কের কর্নারে গ্রাউন্ড ফ্লোর রিটেল স্পেস। ব্যাংক, ডায়াগনস্টিক সেন্টার বা বড় ব্র্যান্ডের শো-রুমের জন্য উপযুক্ত।', 6, 4, 2, '১২০৪ মেইন রোড, কক্সবাজার', 85000, 0, 1, 2400, 2011, 'RENT', 'AVAILABLE', 'N', NOW() - INTERVAL '100 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (17, 'রাজশাহী উপশহরে ফ্যামিলি হোম', '৪ বেডের সুন্দর পরিবারবান্ধব বাড়ি। ড্রয়িং-ডাইনিং স্পেস প্রশস্ত এবং শিশুদের খেলার জায়গা রয়েছে।', 1, 5, 5, '৪৬ উপশহর আবাসিক এলাকা, রাজশাহী', 71500000, 4, 3, 2950, 2017, 'SALE', 'AVAILABLE', 'N', NOW() - INTERVAL '220 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (18, 'রাজশাহী কাজিহাটায় গার্ডেন ফ্ল্যাট', '৩ বেডের খোলামেলা ফ্ল্যাট, নিজস্ব বাগান ও খোলামেলা প্যাটিওসহ। শান্ত নিরিবিলি আবাসিক পরিবেশ।', 2, 5, 3, '৯২ কাজিহাটা মেইন রোড, রাজশাহী', 34000, 3, 2, 1550, 2013, 'RENT', 'AVAILABLE', 'N', NOW() - INTERVAL '210 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (19, 'ধানমন্ডিতে লেকভিউ ডুপ্লেক্স', 'ধানমন্ডি লেকের নিকটে ৩ বেডের অপরূপ ডুপ্লেক্স অ্যাপার্টমেন্ট। প্রশস্ত ব্যালকনি ও ছায়াঘেরা চারপাশ।', 1, 1, 4, 'রোড ৮/এ, ধানমন্ডি, ঢাকা', 59000000, 3, 2, 2200, 2009, 'SALE', 'AVAILABLE', 'N', NOW() - INTERVAL '240 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (20, 'কক্সবাজারে লাক্সারি সী-ভিউ কনডো', 'সরাসরি সমুদ্রের গর্জন শোনা যায় এমন ব্যালকনি সংবলিত ৩ বেডের কনডো। ভ্যালেট পার্কিং ও রিসোর্ট সুবিধা।', 3, 4, 2, '২৫০ সী-ইন পয়েন্ট রোড, ফ্ল্যাট ১৭০১, কক্সবাজার', 109500000, 3, 3, 2100, 2019, 'SALE', 'AVAILABLE', 'N', NOW() - INTERVAL '205 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (21, 'বরিশাল সদর রোডে স্টাইলিশ ফ্ল্যাট', 'সদর রোডের নিকটে ১ বেডের আধুনিক ও রুচিশীল ফ্ল্যাট। চাকুরিজীবীদের জন্য উপযুক্ত ও নিরাপদ।', 2, 7, 3, '১৯ জেল রোড, ফ্ল্যাট ৪, বরিশাল', 27500, 1, 1, 850, 2007, 'RENT', 'AVAILABLE', 'N', NOW() - INTERVAL '165 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (22, 'খুলনা রূপসা তীরে রিভার ভিলা', 'রূপসা নদীর তীরে ৫ বেডের সুবিশাল বাংলো ভিলা। সেন্ট্রাল উঠান, সুইমিং পুল এবং ছাদ থেকে রূপসার সূর্যাস্তের দৃশ্য।', 4, 6, 5, '১৫ রূপসা রিভার ভিউ রোড, খুলনা', 134000000, 5, 4, 4200, 2021, 'SALE', 'PENDING', 'N', NOW() - INTERVAL '40 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (23, 'সিলেটে সবুজ টিলাঘেরা বাড়ি', 'শাহজালাল বিশ্ববিদ্যালয়ের নিকটে ২ বেডের নিরিবিলি সুন্দর বাড়ি। সামনে সবুজ লন ও চমৎকার আবাহাওয়া।', 1, 3, 4, '৮৮ কুমারগাঁও রোড, সিলেট', 55200000, 2, 1, 1150, 1995, 'SALE', 'AVAILABLE', 'N', NOW() - INTERVAL '230 days');

INSERT INTO properties (property_id, title, description, type_id, city_id, agent_id, address, price, bedrooms, bathrooms, area_sqft, year_built, listing_type, status, featured, created_at)
VALUES (24, 'রংপুর জিলা স্কুল রোডে আধুনিক ফ্ল্যাট', 'শহরের প্রাণকেন্দ্রে আধুনিক সুযোগ-সুবিধাসহ স্টুডিও অ্যাপার্টমেন্ট। ছাদবাগান ও নিরাপত্তা ব্যবস্থা চমৎকার।', 2, 8, 5, '৭৪০ জিলা স্কুল রোড, ইউনিট ৩১১, রংপুর', 16500, 1, 1, 700, 2020, 'RENT', 'PENDING', 'N', NOW() - INTERVAL '55 days');

-- ----------------------------------------------------------------------------
--  Property images (ছবিসমূহ)
-- ----------------------------------------------------------------------------
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (1,  1,  '/static/img/prop-01.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (2,  2,  '/static/img/prop-02.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (3,  3,  '/static/img/prop-03.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (4,  4,  '/static/img/prop-04.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (5,  5,  '/static/img/prop-05.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (6,  6,  '/static/img/prop-06.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (7,  7,  '/static/img/prop-07.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (8,  8,  '/static/img/prop-08.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (9,  9,  '/static/img/prop-01.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (10, 10, '/static/img/prop-02.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (11, 11, '/static/img/prop-03.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (12, 12, '/static/img/prop-04.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (13, 13, '/static/img/prop-05.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (14, 14, '/static/img/prop-06.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (15, 15, '/static/img/prop-07.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (16, 16, '/static/img/prop-08.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (17, 17, '/static/img/prop-01.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (18, 18, '/static/img/prop-02.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (19, 19, '/static/img/prop-03.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (20, 20, '/static/img/prop-04.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (21, 21, '/static/img/prop-05.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (22, 22, '/static/img/prop-06.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (23, 23, '/static/img/prop-07.jpg', 'Y');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (24, 24, '/static/img/prop-08.jpg', 'Y');

INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (25, 1,  '/static/img/prop-05.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (26, 1,  '/static/img/prop-06.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (27, 2,  '/static/img/prop-07.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (28, 2,  '/static/img/prop-08.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (29, 3,  '/static/img/prop-01.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (30, 3,  '/static/img/prop-02.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (31, 4,  '/static/img/prop-03.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (32, 4,  '/static/img/prop-05.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (33, 5,  '/static/img/prop-06.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (34, 5,  '/static/img/prop-07.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (35, 6,  '/static/img/prop-08.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (36, 6,  '/static/img/prop-01.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (37, 7,  '/static/img/prop-02.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (38, 7,  '/static/img/prop-03.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (39, 8,  '/static/img/prop-04.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (40, 8,  '/static/img/prop-05.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (41, 9,  '/static/img/prop-06.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (42, 9,  '/static/img/prop-07.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (43, 10, '/static/img/prop-08.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (44, 10, '/static/img/prop-01.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (45, 11, '/static/img/prop-02.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (46, 11, '/static/img/prop-04.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (47, 12, '/static/img/prop-05.jpg', 'N');
INSERT INTO property_images (image_id, property_id, image_url, is_primary) VALUES (48, 12, '/static/img/prop-06.jpg', 'N');

-- ----------------------------------------------------------------------------
--  Property amenities bridge
-- ----------------------------------------------------------------------------
INSERT INTO property_amenities (property_id, amenity_id) VALUES (1,  2);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (1,  3);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (1,  5);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (1,  7);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (1,  8);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (2,  5);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (2,  7);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (2,  9);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (3,  1);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (3,  2);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (3,  3);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (3,  4);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (3,  8);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (3,  12);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (4,  2);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (4,  3);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (4,  8);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (5,  4);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (5,  5);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (5,  7);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (5,  8);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (5,  9);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (6,  3);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (6,  6);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (6,  10);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (7,  6);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (7,  7);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (7,  8);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (7,  9);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (8,  2);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (8,  3);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (8,  6);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (8,  8);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (9,  5);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (9,  7);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (10, 3);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (10, 6);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (10, 7);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (11, 1);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (11, 2);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (11, 3);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (11, 5);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (11, 8);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (11, 12);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (12, 4);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (12, 5);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (12, 7);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (12, 8);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (13, 2);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (13, 3);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (13, 10);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (14, 2);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (14, 4);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (14, 5);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (14, 7);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (14, 8);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (14, 12);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (15, 2);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (15, 10);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (16, 6);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (16, 8);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (16, 9);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (17, 2);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (17, 3);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (17, 11);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (18, 3);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (18, 5);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (18, 10);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (19, 2);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (19, 3);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (19, 5);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (19, 6);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (20, 4);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (20, 5);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (20, 7);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (20, 8);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (21, 5);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (21, 7);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (22, 1);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (22, 2);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (22, 3);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (22, 8);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (23, 3);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (23, 10);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (24, 7);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (24, 8);
INSERT INTO property_amenities (property_id, amenity_id) VALUES (24, 12);

-- ----------------------------------------------------------------------------
--  Inquiries (অনুসন্ধান বার্তাসমূহ)
-- ----------------------------------------------------------------------------
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (1, 6, 'আমরা বাড়িটি সামনাসামনি দেখতে আগ্রহী। আগামী শুক্রবারে কি সময় দেওয়া যাবে?', CURRENT_DATE + INTERVAL '5 days', 'NEW', NOW() - INTERVAL '3 days');
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (1, 7, 'বাড়িটির দলিলপত্র ও রাজউক অনুমোদিত প্ল্যান কি সম্পূর্ণ প্রস্তুত আছে?', CURRENT_DATE + INTERVAL '7 days', 'CONTACTED', NOW() - INTERVAL '12 days');
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (3, 8, 'ভিলাটিতে আগ্রহী। সুইমিং পুলের রক্ষণাবেক্ষণ ব্যবস্থা কেমন দয়া করে জানাবেন।', CURRENT_DATE + INTERVAL '4 days', 'NEW', NOW() - INTERVAL '2 days');
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (5, 6, 'কনডোটির মাসিক সার্ভিস চার্জ ও অন্যান্য খরচের বিবরণ কি পাঠানো সম্ভব?', CURRENT_DATE + INTERVAL '6 days', 'CONTACTED', NOW() - INTERVAL '9 days');
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (5, 9, 'পার্কিং স্পেস কি নির্দিষ্ট বরাদ্দ নাকি শেয়ার্ড?', CURRENT_DATE + INTERVAL '3 days', 'NEW', NOW() - INTERVAL '1 days');
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (8, 7, 'আমরা প্রকৌশলী সঙ্গে নিয়ে প্রপার্টি পরিদর্শন করতে চাই। আপনাদের সুবিধাজনক সময় জানান।', CURRENT_DATE + INTERVAL '8 days', 'CONTACTED', NOW() - INTERVAL '15 days');
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (11, 9, 'বিক্রয়ের মূল্যের সাথে কি ফার্নিচার ও ফিটিংস অন্তর্ভুক্ত থাকবে?', CURRENT_DATE + INTERVAL '10 days', 'NEW', NOW() - INTERVAL '4 days');
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (12, 8, 'আমরা আগামী মাস থেকে দুই বছরের চুক্তিতে ভাড়া নিতে চাই। আলোচনা সম্ভব?', CURRENT_DATE + INTERVAL '2 days', 'CONTACTED', NOW() - INTERVAL '6 days');
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (14, 6, 'পেন্টহাউসটির হোল্ডিং ট্যাক্স এবং ইউটিলিটি বিলের অবস্থা সম্পর্কে জানতে চাই।', CURRENT_DATE + INTERVAL '9 days', 'NEW', NOW() - INTERVAL '5 days');
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (17, 6, 'আমরা তালিকাভুক্ত মূল্যে বাড়িটি কিনতে প্রস্তুত আছি। চুক্তি প্রক্রিয়া শুরু করতে চাই।', CURRENT_DATE - INTERVAL '30 days', 'CLOSED', NOW() - INTERVAL '60 days');
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (19, 7, 'দ্বিতীয়বার পরিদর্শনের পর আমরা সন্তুষ্ট। বিক্রেতার সাথে বায়না চুক্তি করতে চাই।', CURRENT_DATE - INTERVAL '40 days', 'CLOSED', NOW() - INTERVAL '75 days');
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (22, 8, 'রেজিস্ট্রেশনের জন্য কিছুটা সময় পাওয়া যাবে কি না জানতে চাচ্ছি।', CURRENT_DATE + INTERVAL '12 days', 'CONTACTED', NOW() - INTERVAL '8 days');
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (3, 9, 'শনিবার সকালে আমরা ভিলা দেখতে আসব। দয়া করে যোগাযোগের লোকেশন ম্যাপ পাঠান।', CURRENT_DATE + INTERVAL '3 days', 'SCHEDULED', NOW() - INTERVAL '7 days');
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (11, 6, 'আগামী সপ্তাহে পরিদর্শনের সময় নির্ধারণ করা হয়েছে, সেসময়ে কি উপস্থিত থাকবেন?', CURRENT_DATE + INTERVAL '5 days', 'SCHEDULED', NOW() - INTERVAL '11 days');
INSERT INTO inquiries (property_id, customer_id, message, preferred_date, status, created_at)
VALUES (14, 7, 'বৃহস্পতিবার দুপুর ২টায় মিটিং নিশ্চিত করেছি। অনসাইট কার পার্কিং কি পাওয়া যাবে?', CURRENT_DATE + INTERVAL '4 days', 'SCHEDULED', NOW() - INTERVAL '5 days');

-- ----------------------------------------------------------------------------
--  Transactions (লেনদেন ও বিক্রয় রেকর্ড)
-- ----------------------------------------------------------------------------
INSERT INTO transactions (property_id, buyer_id, agent_id, sale_price, txn_type, txn_date)
VALUES (17, 6, 5, 71500000, 'SALE', '2026-02-14');
INSERT INTO transactions (property_id, buyer_id, agent_id, sale_price, txn_type, txn_date)
VALUES (19, 7, 4, 59000000, 'SALE', '2026-03-05');
INSERT INTO transactions (property_id, buyer_id, agent_id, sale_price, txn_type, txn_date)
VALUES (18, 8, 3, 34000,    'RENT', '2026-03-22');
INSERT INTO transactions (property_id, buyer_id, agent_id, sale_price, txn_type, txn_date)
VALUES (20, 9, 2, 109500000,'SALE', '2026-04-18');
INSERT INTO transactions (property_id, buyer_id, agent_id, sale_price, txn_type, txn_date)
VALUES (21, 6, 3, 27500,    'RENT', '2026-05-09');
INSERT INTO transactions (property_id, buyer_id, agent_id, sale_price, txn_type, txn_date)
VALUES (23, 7, 4, 55200000, 'SALE', '2026-06-27');

-- ----------------------------------------------------------------------------
--  Reviews (এজেন্টদের জন্য কাস্টমার রিভিউ)
-- ----------------------------------------------------------------------------
INSERT INTO reviews (agent_id, customer_id, rating, comments, review_date)
VALUES (2, 6, 5, 'সাদিয়া প্রতিটি প্রশ্নের খুব দ্রুত উত্তর দিয়েছেন এবং পুরো প্রপার্টি ক্রয়ের অভিজ্ঞতা অনেক সহজ করে তুলেছেন।', NOW() - INTERVAL '50 days');
INSERT INTO reviews (agent_id, customer_id, rating, comments, review_date)
VALUES (2, 7, 4, 'এলাকা এবং কাগজপত্র সম্পর্কে উনার গভীর ধারণা রয়েছে। সার্ভিস অত্যন্ত চমৎকার।', NOW() - INTERVAL '44 days');
INSERT INTO reviews (agent_id, customer_id, rating, comments, review_date)
VALUES (2, 9, 5, 'কক্সবাজারের কনডো কেনার ক্ষেত্রে উনি আমাদের অনেক সহায়তা করেছেন এবং উপযুক্ত মূল্যে ডিল সম্পন্ন করেছেন।', NOW() - INTERVAL '20 days');
INSERT INTO reviews (agent_id, customer_id, rating, comments, review_date)
VALUES (3, 6, 4, 'সিলেট ও ঢাকার চমৎকার কিছু ফ্ল্যাট দেখিয়েছেন এবং সঠিক পরামর্শ দিয়েছেন।', NOW() - INTERVAL '38 days');
INSERT INTO reviews (agent_id, customer_id, rating, comments, review_date)
VALUES (3, 8, 5, 'তানভীর মাত্র এক সপ্তাহের মধ্যে আমাদের জন্য উপযুক্ত অফিস স্পেস খুঁজে দিয়েছেন।', NOW() - INTERVAL '30 days');
INSERT INTO reviews (agent_id, customer_id, rating, comments, review_date)
VALUES (4, 7, 5, 'নুসরাত অত্যন্ত দায়িত্বশীলভাবে পুরো ক্রয় প্রক্রিয়া শেষ করিয়েছেন। উনার যোগাযোগ দক্ষতা দারুণ।', NOW() - INTERVAL '25 days');
INSERT INTO reviews (agent_id, customer_id, rating, comments, review_date)
VALUES (4, 8, 3, 'সার্ভিস ভালো, যদিও প্রথমদিকে কিছুটা সময় বেশি লেগেছিল তবে শেষ পর্যন্ত ডিল সম্পন্ন হয়েছে।', NOW() - INTERVAL '18 days');
INSERT INTO reviews (agent_id, customer_id, rating, comments, review_date)
VALUES (5, 9, 4, 'আরিফুল ভিলা ও রিসোর্ট মার্কেট খুব ভালো বোঝেন এবং পুরো প্রক্রিয়ায় অনেক ধৈর্যশীল ছিলেন।', NOW() - INTERVAL '33 days');
INSERT INTO reviews (agent_id, customer_id, rating, comments, review_date)
VALUES (5, 6, 5, 'খুবই পেশাদার ও সৎ এজেন্ট। কখনোই অপ্রয়োজনীয় চাপ দেননি। ভবিষ্যতে আবারও উনার মাধ্যমে লেনদেন করতে চাই।', NOW() - INTERVAL '12 days');

-- ----------------------------------------------------------------------------
--  Favorites (সংরক্ষিত পছন্দের তালিকা)
-- ----------------------------------------------------------------------------
INSERT INTO favorites (user_id, property_id, added_at) VALUES (6, 1,  NOW() - INTERVAL '10 days');
INSERT INTO favorites (user_id, property_id, added_at) VALUES (6, 5,  NOW() - INTERVAL '9 days');
INSERT INTO favorites (user_id, property_id, added_at) VALUES (6, 14, NOW() - INTERVAL '4 days');
INSERT INTO favorites (user_id, property_id, added_at) VALUES (7, 1,  NOW() - INTERVAL '13 days');
INSERT INTO favorites (user_id, property_id, added_at) VALUES (7, 8,  NOW() - INTERVAL '11 days');
INSERT INTO favorites (user_id, property_id, added_at) VALUES (7, 3,  NOW() - INTERVAL '2 days');
INSERT INTO favorites (user_id, property_id, added_at) VALUES (8, 3,  NOW() - INTERVAL '7 days');
INSERT INTO favorites (user_id, property_id, added_at) VALUES (8, 12, NOW() - INTERVAL '6 days');
INSERT INTO favorites (user_id, property_id, added_at) VALUES (9, 11, NOW() - INTERVAL '5 days');
INSERT INTO favorites (user_id, property_id, added_at) VALUES (9, 14, NOW() - INTERVAL '3 days');
INSERT INTO favorites (user_id, property_id, added_at) VALUES (9, 22, NOW() - INTERVAL '1 days');

-- ----------------------------------------------------------------------------
--  Row counts verification query
-- ----------------------------------------------------------------------------
SELECT 'roles'              AS table_name, COUNT(*) AS row_count FROM roles
UNION ALL SELECT 'cities',             COUNT(*) FROM cities
UNION ALL SELECT 'property_types',     COUNT(*) FROM property_types
UNION ALL SELECT 'amenities',          COUNT(*) FROM amenities
UNION ALL SELECT 'users',              COUNT(*) FROM users
UNION ALL SELECT 'agents',             COUNT(*) FROM agents
UNION ALL SELECT 'properties',         COUNT(*) FROM properties
UNION ALL SELECT 'property_images',    COUNT(*) FROM property_images
UNION ALL SELECT 'property_amenities', COUNT(*) FROM property_amenities
UNION ALL SELECT 'inquiries',          COUNT(*) FROM inquiries
UNION ALL SELECT 'transactions',       COUNT(*) FROM transactions
UNION ALL SELECT 'reviews',            COUNT(*) FROM reviews
UNION ALL SELECT 'favorites',          COUNT(*) FROM favorites
UNION ALL SELECT 'audit_log (trigger)', COUNT(*) FROM audit_log;

-- ----------------------------------------------------------------------------
--  Reset sequence values so subsequent SERIAL inserts succeed
-- ----------------------------------------------------------------------------
SELECT setval(pg_get_serial_sequence('roles', 'role_id'), coalesce(max(role_id), 1)) FROM roles;
SELECT setval(pg_get_serial_sequence('cities', 'city_id'), coalesce(max(city_id), 1)) FROM cities;
SELECT setval(pg_get_serial_sequence('property_types', 'type_id'), coalesce(max(type_id), 1)) FROM property_types;
SELECT setval(pg_get_serial_sequence('amenities', 'amenity_id'), coalesce(max(amenity_id), 1)) FROM amenities;
SELECT setval(pg_get_serial_sequence('users', 'user_id'), coalesce(max(user_id), 1)) FROM users;
SELECT setval(pg_get_serial_sequence('properties', 'property_id'), coalesce(max(property_id), 1)) FROM properties;
SELECT setval(pg_get_serial_sequence('property_images', 'image_id'), coalesce(max(image_id), 1)) FROM property_images;
SELECT setval(pg_get_serial_sequence('inquiries', 'inquiry_id'), coalesce(max(inquiry_id), 1)) FROM inquiries;
SELECT setval(pg_get_serial_sequence('transactions', 'transaction_id'), coalesce(max(transaction_id), 1)) FROM transactions;
SELECT setval(pg_get_serial_sequence('reviews', 'review_id'), coalesce(max(review_id), 1)) FROM reviews;
SELECT setval(pg_get_serial_sequence('audit_log', 'log_id'), coalesce(max(log_id), 1)) FROM audit_log;

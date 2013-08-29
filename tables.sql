DROP TABLE IF EXISTS `students`;
CREATE TABLE `students` (
	`id` int NOT NULL AUTO_INCREMENT,
	`last_name` varchar(128),
	`first_name` varchar(128),
	`grade` int,
	`last_event` int, 

	PRIMARY KEY (`id`)
);

DROP TABLE IF EXISTS `documents`;
CREATE TABLE `documents` (
	`id` int NOT NULL AUTO_INCREMENT,
	`file_name` varchar(256),
	`file_path` varchar(512),
	`student_id` int,

	PRIMARY KEY (`id`)
);

DROP TABLE IF EXISTS `events`;
CREATE TABLE `events` (
	`id` int NOT NULL AUTO_INCREMENT,
	`name` varchar(128),
	`time` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
	`student_id` int,
	`event_type_id` int,
	`direction` varchar(16),
	`author` varchar(32),
	`ip_address` varchar(32),

	PRIMARY KEY (`id`)
);

DROP TABLE IF EXISTS `event_types`;
CREATE TABLE `event_types` (
	`id` int NOT NULL AUTO_INCREMENT,
	`name` varchar(128),

	PRIMARY KEY (`id`)

);
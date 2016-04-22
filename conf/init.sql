drop database if exists `webapp`;

create database `webapp` ;

use `webapp` ;

grant select, insert, update, delete on webapp.* to 'yuhari'@'%' identified by 'yuhari' ;

drop table if exists `users` ;
create table `users`(
    `id` varchar(50) not null,
    `email` varchar(50) not null,
    `passwd` varchar(50) not null,
    `admin` bool not null,
    `name` varchar(50) not null,
    `image` varchar(500) not null,
    `created_time` real not null,
    unique key `idx_email` (`email`),
    key `idx_created_time` (`created_time`),
    primary key (`id`)
)engine=InnoDB default charset=utf8 ;

drop table if exists `blogs` ;
create table `blogs`(
	`id` varchar(50) not null,
	`user_id` varchar(50) not null,
	`user_name` varchar(50) not null,
	`user_image` varchar(500) not null,
	`name` varchar(50) not null,
	`summary` varchar(200) not null,
	`content` mediumtext not null,
	`created_time` real not null,
	key `idx_created_time` (`created_time`),
	key `idx_user_id` (`user_id`),
	primary key (`id`)
)engine=InnoDB default charset=utf8 ;

drop table if exists `comments` ;
create table `comments`(
    `id` varchar(50) not null,
    `blog_id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `content` mediumtext not null,
    `created_time` real not null,
    key `idx_created_time` (`created_time`),
	key `idx_user_id` (`user_id`),
	key `idx_blog_id` (`blog_id`),
    primary key (`id`)
)engine=InnoDB default charset=utf8;
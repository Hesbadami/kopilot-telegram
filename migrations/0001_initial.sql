CREATE TABLE IF NOT EXISTS `user` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `user_id` BIGINT UNIQUE NOT NULL,
    `first_name` VARCHAR(255) NOT NULL,
    `last_name` VARCHAR(255),
    `username` VARCHAR(255),
    `can_chat` BOOLEAN DEFAULT FALSE,
    `photo` VARCHAR(255) NULL,
    `photo_file_id` VARCHAR(255) NULL,
    `is_deleted` BOOLEAN DEFAULT FALSE,
    `phone` VARCHAR(255) NULL,
    `is_bot` BOOLEAN DEFAULT FALSE,
    `date_created` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    `date_modified` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_phone` (`phone`),
    INDEX `idx_is_deleted` (`is_deleted`)
);

CREATE TABLE IF NOT EXISTS `chat` (
    `id`  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `chat_id` BIGINT UNIQUE NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `photo` VARCHAR(255) NULL,
    `photo_file_id` VARCHAR(255) NULL,
    `accent_color` VARCHAR(7),
    `invite_link` VARCHAR(255),
    `is_deleted` BOOLEAN DEFAULT FALSE,
    `date_created` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    `date_modified` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    INDEX `idx_chat_id` (`chat_id`)
);

CREATE TABLE IF NOT EXISTS `chatmember` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `chat_id` BIGINT NOT NULL,
    `user_id` BIGINT NOT NULL,
    `status` ENUM('member', 'administrator', 'creator', 'restricted', 'left', 'kicked', 'banned') NOT NULL,
    `custom_title` VARCHAR(255) NULL,
    `joined_at` DATETIME(6) NOT NULL,
    `left_at` DATETIME(6) NULL,
    `is_muted` BOOLEAN DEFAULT FALSE,
    `can_send_messages` BOOLEAN DEFAULT TRUE,
    `can_delete_messages` BOOLEAN DEFAULT FALSE,
    `date_created` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    `date_modified` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    CONSTRAINT `fk_chatmember_chat` 
        FOREIGN KEY (`chat_id`) REFERENCES `chat`(`chat_id`) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    
    CONSTRAINT `fk_chatmember_user` 
        FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`) 
        ON DELETE CASCADE ON UPDATE CASCADE,

    UNIQUE KEY `uk_chat_user` (`chat_id`, `user_id`),
    INDEX `idx_chat_id` (`chat_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_status` (`status`)
);

CREATE TABLE IF NOT EXISTS `message` (
    `id`  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `message_id` BIGINT NOT NULL,
    `chatmember_id` BIGINT UNSIGNED NOT NULL,
    `user_id` BIGINT NOT NULL,
    `chat_id` BIGINT NOT NULL,
    `date` DATETIME(6) NOT NULL,
    `reply_to_message_id` BIGINT UNSIGNED NULL,
    `type` ENUM(
        'text', 'animation', 'audio', 'document',
        'photo', 'sticker', 'video', 'video_note',
        'voice', 'other'
    ),
    `is_external_forward` BOOLEAN DEFAULT FALSE,
    `is_deleted` BOOLEAN DEFAULT FALSE,
    `date_created` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    `date_modified` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    CONSTRAINT `fk_message_chatmember` 
        FOREIGN KEY (`chatmember_id`) REFERENCES `chatmember`(`id`) 
        ON DELETE CASCADE ON UPDATE CASCADE,
        
    CONSTRAINT `fk_message_user` 
        FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    
    CONSTRAINT `fk_message_chat` 
        FOREIGN KEY (`chat_id`) REFERENCES `chat`(`chat_id`) 
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT `fk_message_reply` 
        FOREIGN KEY (`reply_to_message_id`) REFERENCES `message`(`id`) 
        ON DELETE SET NULL ON UPDATE CASCADE,

    INDEX `idx_message_id` (`message_id`),
    INDEX `idx_chatmember_id` (`chatmember_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_chat_id` (`chat_id`),
    INDEX `idx_date` (`date`),
    INDEX `idx_reply_to_message_id` (`reply_to_message_id`),
    INDEX `idx_is_deleted` (`is_deleted`),
    INDEX `idx_is_external_forward` (`is_external_forward`),
    INDEX `idx_type` (`type`),
    INDEX `idx_chat_user` (`chat_id`, `user_id`),
    INDEX `idx_user_date` (`user_id`, `date`),
    INDEX `idx_user_deleted_date` (`user_id`, `is_deleted`, `date`)
);

CREATE TABLE IF NOT EXISTS `reaction` (
    `id`  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `message_id` BIGINT UNSIGNED NOT NULL,
    `chatmember_id` BIGINT UNSIGNED NOT NULL,
    `user_id` BIGINT NOT NULL,
    `chat_id` BIGINT NOT NULL,
    `date` DATETIME(6) NOT NULL,
    `is_deleted` BOOLEAN DEFAULT FALSE,
    `date_created` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    `date_modified` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    CONSTRAINT `fk_reaction_chatmember` 
        FOREIGN KEY (`chatmember_id`) REFERENCES `chatmember`(`id`) 
        ON DELETE CASCADE ON UPDATE CASCADE,
        
    CONSTRAINT `fk_reaction_user` 
        FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    
    CONSTRAINT `fk_reaction_chat` 
        FOREIGN KEY (`chat_id`) REFERENCES `chat`(`chat_id`) 
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT `fk_reaction_message` 
        FOREIGN KEY (`message_id`) REFERENCES `message`(`id`) 
        ON DELETE CASCADE ON UPDATE CASCADE,

    INDEX `idx_chatmember_id` (`chatmember_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_chat_id` (`chat_id`),
    INDEX `idx_date` (`date`),
    INDEX `idx_is_deleted` (`is_deleted`)
);
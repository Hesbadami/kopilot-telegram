ALTER TABLE `kopilot_telegram`.`chatmember`
ADD COLUMN `added_by` BIGINT NULL,
ADD COLUMN `removed_by` BIGINT NULL,
ADD CONSTRAINT `fk_chat_added_by` FOREIGN KEY (`added_by`) REFERENCES `user`(`user_id`) ON DELETE SET NULL ON UPDATE CASCADE,
ADD CONSTRAINT `fk_chat_removed_by` FOREIGN KEY (`removed_by`) REFERENCES `user`(`user_id`) ON DELETE SET NULL ON UPDATE CASCADE;
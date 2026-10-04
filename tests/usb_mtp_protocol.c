/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "buildconf.h"
#include <assert.h>
#include <inttypes.h>
#include <pthread.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "mtp.h"
#include "mtp_helpers.h"
#include "mtp_constant.h"
#include "mtp_operations.h"
#include "usb_gadget.h"
#include "mtp_ops_helpers.h"
extern mtp_ctx *mtp_context;
extern usb_gadget *init_usb_mtp_gadget(mtp_ctx *);
extern void deinit_usb_mtp_gadget(usb_gadget *);
extern void fill_if_descriptor(mtp_ctx *, usb_gadget *, struct usb_interface_descriptor *);
extern void fill_ep_descriptor(mtp_ctx *, usb_gadget *, struct usb_endpoint_descriptor_no_audio *, int, unsigned);
/* Link the actual operation/parser/descriptor code with isolated media and a
 * pipe for host OUT packets. No device, gadget bind or raw sector operation. */
int main(int argc, char **argv)
{
    assert(argc==2);
    mtp_ctx ctx={0}; usb_gadget usb={0}; int channel[2];
    assert(!pipe(channel)); mtp_context=&ctx;
    ctx.usb_ctx=&usb; usb.ep_handles[EP_DESCRIPTOR_OUT]=channel[0];
    ctx.uid=getuid(); ctx.euid=geteuid(); ctx.gid=getgid(); ctx.egid=getegid();
    ctx.default_uid=ctx.default_gid=-1;
    ctx.usb_rd_buffer_max_size=8192;
    ctx.rdbuffer2=calloc(1,8192);
    ctx.wrbuffer=calloc(1,8192); ctx.usb_wr_buffer_max_size=8192; ctx.max_packet_size=512;
    ctx.usb_cfg.usb_class=6; ctx.usb_cfg.usb_subclass=1; ctx.usb_cfg.usb_protocol=1;
    struct usb_interface_descriptor interface;
    struct usb_endpoint_descriptor_no_audio endpoint;
    fill_if_descriptor(&ctx,&usb,&interface);
    assert(interface.bInterfaceClass==6 && interface.bNumEndpoints==3);
    fill_ep_descriptor(&ctx,&usb,&endpoint,1,EP_BULK_MODE|EP_IN_DIR|EP_HS_MODE);
    assert(endpoint.wMaxPacketSize==512 && endpoint.bEndpointAddress==0x81);
    fill_ep_descriptor(&ctx,&usb,&endpoint,2,EP_BULK_MODE|EP_OUT_DIR);
    assert(endpoint.wMaxPacketSize==64 && endpoint.bEndpointAddress==2);
    fill_ep_descriptor(&ctx,&usb,&endpoint,3,EP_INT_MODE|EP_IN_DIR);
    assert(endpoint.wMaxPacketSize==16 && endpoint.bInterval>0);
    /* Capture exactly the descriptor block the daemon writes before UDC bind,
     * including Windows MTP compatible-ID descriptors (no live gadget). */
    char ep0[4096]; snprintf(ep0,sizeof ep0,"%s/ep0.fixture",argv[1]);
    int descriptor=open(ep0,O_RDWR|O_CREAT|O_EXCL,0600); assert(descriptor>=0);
    ctx.usb_cfg.usb_functionfs_mode=1;
    snprintf(ctx.usb_cfg.usb_device_path,sizeof ctx.usb_cfg.usb_device_path,"%s",ep0);
    strcpy(ctx.usb_cfg.usb_string_manufacturer,"Y2Linux");
    strcpy(ctx.usb_cfg.usb_string_product,"Y2");
    strcpy(ctx.usb_cfg.usb_string_serial,"Y2LINUX-DEV-01");
    strcpy(ctx.usb_cfg.usb_string_interface,"MTP");
    usb_gadget *captured=init_usb_mtp_gadget(&ctx); assert(captured);
    usb_ffs_cfg emitted; assert(pread(descriptor,&emitted,sizeof emitted,0)==sizeof emitted);
    assert(emitted.magic==FUNCTIONFS_DESCRIPTORS_MAGIC_V2 && emitted.length==sizeof emitted);
    assert((emitted.flags & (FUNCTIONFS_HAS_FS_DESC|FUNCTIONFS_HAS_HS_DESC|FUNCTIONFS_HAS_MS_OS_DESC)) ==
           (FUNCTIONFS_HAS_FS_DESC|FUNCTIONFS_HAS_HS_DESC|FUNCTIONFS_HAS_MS_OS_DESC));
    assert(emitted.fs_count==4 && emitted.hs_count==4 && emitted.os_count==1);
    assert(emitted.os_header.interface==0 && emitted.os_header.bcdVersion==0x0100 && emitted.os_header.wIndex==4);
    assert(emitted.os_header.dwLength==sizeof(struct usb_os_desc_header)+sizeof(struct usb_ext_compat_desc));
    assert(emitted.os_header.bCount==1 && emitted.os_compat.Reserved1==1 && !memcmp(emitted.os_compat.CompatibleID,"MTP",3));
    assert(emitted.ep_desc_hs.ep_desc_int_in.wMaxPacketSize==16 && emitted.ep_desc_hs.if_desc.bInterfaceClass==6);
    deinit_usb_mtp_gadget(captured); close(descriptor); assert(!unlink(ep0));
    ctx.usb_ctx=&usb; ctx.rdbuffer2=calloc(1,8192); ctx.wrbuffer=calloc(1,8192);
    pthread_mutex_init(&ctx.inotify_mutex,NULL);
    assert(!y2_fs_init(argv[1],NULL,NULL));
    uint32_t store=mtp_add_storage(&ctx,argv[1],"Internal Storage",-1,-1,0);
    assert(store && store!=UINT32_MAX);
    ctx.fs_db=init_fs_db(&ctx); assert(ctx.fs_db);
    assert(alloc_root_entry(ctx.fs_db,store));
    for(unsigned iteration=0;iteration<5;iteration++) {
        unsigned char info[256]={0}, command[32]={0}, data[32]={0};
        char name[64], path[4096]; snprintf(name,sizeof name,"copy-%u.flac",iteration);
        snprintf(path,sizeof path,"%s/%s",argv[1],name);
        MTP_PACKET_HEADER *ih=(void *)info, *ch=(void *)command, *dh=(void *)data;
        ih->code=MTP_OPERATION_SEND_OBJECT_INFO; ih->operation=MTP_CONTAINER_TYPE_DATA;
        unsigned char *dataset=info+sizeof *ih;
        dataset[4]=0; dataset[5]=0x30; /* undefined file format */
        dataset[8]=6; dataset[0x34]=strlen(name)+1;
        for(unsigned i=0;i<strlen(name);i++) dataset[0x35+2*i]=name[i];
        int length=sizeof *ih+0x35+2*(strlen(name)+1);
        ih->length=length;
        ch->code=MTP_OPERATION_SEND_OBJECT_INFO; ch->operation=MTP_CONTAINER_TYPE_COMMAND;
        memcpy(command+sizeof *ch,&store,4);
        assert(write(channel[1],info,length)==length);
        int size=sizeof *ch+8, params_size=0; uint32_t params[4]={0};
        assert(mtp_op_SendObjectInfo(&ctx,ch,&size,params,&params_size)==MTP_RESPONSE_OK);
        assert(params_size==12 && params[2]!=UINT32_MAX);
        assert(access(path,F_OK));
        dh->code=MTP_OPERATION_SEND_OBJECT; dh->operation=MTP_CONTAINER_TYPE_DATA;
        memcpy(data+sizeof *dh,"abcdef",6); size=sizeof *dh+6;
        if(iteration==1) size--; /* truncated host copy */
        if(iteration==2) ctx.cancel_req=1;
        if(iteration==3) { deinit_fs_db(ctx.fs_db); ctx.fs_db=NULL; } /* disconnect */
        uint32_t response=mtp_op_SendObject(&ctx,dh,&size,params,&params_size);
        if(iteration==0 || iteration==4) {
            assert(response==MTP_RESPONSE_OK);
            int file=y2_open(path,O_RDONLY,0); char bytes[7]={0}; assert(file>=0);
            assert(read(file,bytes,6)==6 && !strcmp(bytes,"abcdef")); close(file);
            int output[2]; assert(!pipe(output)); usb.ep_handles[EP_DESCRIPTOR_IN]=output[1];
            fs_entry *entry=get_entry_by_handle(ctx.fs_db,params[2]); assert(entry);
            assert(send_file_data(&ctx,entry,0,6)==6);
            unsigned char result[18]={0}; assert(read(output[0],result,sizeof result)==sizeof result);
            assert(!memcmp(result+sizeof(MTP_PACKET_HEADER),"abcdef",6));
            /* Concurrent local truncation is an incomplete transfer, never
             * zero-filled/stale bytes with an OK response. */
            file=open(path,O_TRUNC|O_WRONLY); assert(file>=0); close(file);
            assert(send_file_data(&ctx,entry,0,6)<0);
            close(output[0]); close(output[1]);
        } else assert(access(path,F_OK));
        if(iteration==3) { ctx.fs_db=init_fs_db(&ctx); assert(alloc_root_entry(ctx.fs_db,store)); }
    }
    deinit_fs_db(ctx.fs_db); free(ctx.rdbuffer); free(ctx.rdbuffer2); free(ctx.wrbuffer); close(channel[0]); close(channel[1]);
    puts("PASS FS/HS descriptors, actual SendObjectInfo/SendObject/download: hidden staging, complete, truncated, cancelled, disconnected, new session, concurrent truncation");
}
